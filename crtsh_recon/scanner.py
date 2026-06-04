"""
scanner.py — High-level orchestrator that ties together client, parser and exporter.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .client import CRTClient
from .hackertarget_client import HackerTargetClient
from .parser import extract_subdomains
from .exporter import export_results
from .exceptions import CRTReconError

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Encapsulates every artefact produced by a single scan run."""

    domain: str
    subdomains: list[str] = field(default_factory=list)
    cert_count: int = 0
    hackertarget_count: int = 0
    exported_files: dict[str, Path] = field(default_factory=dict)
    elapsed: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class ScanConfig:
    """Configuration bundle consumed by :func:`run_scan`."""

    domain: str
    formats: list[str] = field(default_factory=lambda: ["txt"])
    output_dir: str = "output"
    timeout: int = 30
    retries: int = 3
    backoff: float = 2.0
    use_hackertarget: bool = True


def run_scan(config: ScanConfig) -> ScanResult:
    """
    Execute a full subdomain enumeration scan for *config.domain*.

    Steps:
    1. Fetch raw certificate records via :class:`CRTClient`.
    2. Optionally fetch from HackerTarget API and merge results.
    3. Parse & deduplicate subdomains with :func:`extract_subdomains`.
    4. Export results in the requested formats.

    Args:
        config: A populated :class:`ScanConfig` instance.

    Returns:
        A :class:`ScanResult` with all findings and metadata.
    """
    result = ScanResult(domain=config.domain)
    start = time.monotonic()

    all_subdomains = set()

    # ─── Fetch from CRT.sh ───────────────────────────────────────────────────
    with CRTClient(
        timeout=config.timeout,
        retries=config.retries,
        backoff=config.backoff,
    ) as client:
        try:
            logger.debug("Starting scan for %s via CRT.sh", config.domain)
            records = client.fetch_certificates(config.domain)
            result.cert_count = len(records)

            subdomains = extract_subdomains(records, config.domain)
            all_subdomains.update(subdomains)
            logger.info("CRT.sh: Found %d subdomain(s)", len(subdomains))

        except CRTReconError as exc:
            logger.warning("CRT.sh scan failed: %s", exc)
            # Don't fail immediately; try HackerTarget if enabled
        except Exception as exc:  # pragma: no cover
            logger.warning("Unexpected error during CRT.sh scan: %s", exc)

    # ─── Fetch from HackerTarget (if enabled) ────────────────────────────────
    if config.use_hackertarget:
        with HackerTargetClient(
            timeout=config.timeout,
            retries=config.retries,
            backoff=config.backoff,
        ) as client:
            try:
                logger.debug("Fetching subdomains from HackerTarget for %s", config.domain)
                ht_subdomains = client.fetch_subdomains(config.domain)
                result.hackertarget_count = len(ht_subdomains)
                all_subdomains.update(ht_subdomains)
                logger.info("HackerTarget: Found %d subdomain(s)", len(ht_subdomains))

            except CRTReconError as exc:
                logger.warning("HackerTarget fetch failed: %s", exc)
            except Exception as exc:  # pragma: no cover
                logger.warning("Unexpected error during HackerTarget fetch: %s", exc)

    # ─── Validate we have results ────────────────────────────────────────────
    if not all_subdomains:
        result.error = (
            f"No subdomains found for {config.domain} from any source. "
            "Ensure the domain is valid and has public certificates."
        )
        result.elapsed = time.monotonic() - start
        return result

    # ─── Sort and prepare for export ─────────────────────────────────────────
    result.subdomains = sorted(all_subdomains)

    # ─── Export results ─────────────────────────────────────────────────────
    if config.formats:
        metadata = {
            "cert_records_fetched": result.cert_count,
            "hackertarget_results": result.hackertarget_count,
            "retries_configured": config.retries,
            "sources": ["crt.sh"] + (["hackertarget"] if config.use_hackertarget else []),
        }
        try:
            result.exported_files = export_results(
                subdomains=result.subdomains,
                domain=config.domain,
                formats=config.formats,
                output_dir=config.output_dir,
                metadata=metadata,
            )
        except CRTReconError as exc:
            logger.error("Export failed: %s", exc)
            result.error = str(exc)

    result.elapsed = time.monotonic() - start
    logger.debug("Scan completed in %.2fs", result.elapsed)
    return result
