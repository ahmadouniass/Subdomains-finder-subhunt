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
from .rapiddns_client import RapidDNSClient
from .prober import probe_subdomains, ProbeResult

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Encapsulates every artefact produced by a single scan run."""

    domain: str
    subdomains: list[str] = field(default_factory=list)
    cert_count: int = 0
    hackertarget_count: int = 0
    rapiddns_count: int = 0
    exported_files: dict[str, Path] = field(default_factory=dict)
    elapsed: float = 0.0
    error: Optional[str] = None
    crtsh_available: bool = True
    probe_results: list[ProbeResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def alive_count(self) -> int:
        return sum(1 for r in self.probe_results if r.alive)

    @property
    def dead_count(self) -> int:
        return sum(1 for r in self.probe_results if not r.alive)


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
    use_rapiddns: bool = True
    probe: bool = False
    alive_only: bool = False
    probe_timeout: int = 5
    probe_workers: int = 20


def run_scan(config: ScanConfig) -> ScanResult:
    """
    Execute a full subdomain enumeration scan for *config.domain*.

    Steps:
    1. Health check CRT.sh availability (quick 5s ping).
    2. Fetch raw certificate records via :class:`CRTClient` (if available).
    3. Optionally fetch from HackerTarget API and merge results.
    4. Optionally fetch from RapidDNS and merge results.
    5. Parse & deduplicate subdomains with :func:`extract_subdomains`.
    6. Optionally probe subdomains for liveness.
    7. Export results in the requested formats.

    Args:
        config: A populated :class:`ScanConfig` instance.

    Returns:
        A :class:`ScanResult` with all findings and metadata.
    """
    result = ScanResult(domain=config.domain)
    start = time.monotonic()

    all_subdomains = set()

    # ─── Health check CRT.sh ─────────────────────────────────────────────────
    with CRTClient(
        timeout=config.timeout,
        retries=config.retries,
        backoff=config.backoff,
    ) as client:
        crtsh_is_healthy = client.health_check(timeout=5)
        result.crtsh_available = crtsh_is_healthy

        if not crtsh_is_healthy:
            logger.warning("CRT.sh appears to be down or unreachable")

    # ─── Fetch from CRT.sh (only if healthy) ────────────────────────────────
    if result.crtsh_available:
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

    # ─── Fetch from RapidDNS (if enabled) ────────────────────────────────────
    if config.use_rapiddns:
        with RapidDNSClient(
            timeout=config.timeout,
            retries=config.retries,
            backoff=config.backoff,
        ) as client:
            try:
                rd_subdomains = client.fetch_subdomains(config.domain)
                result.rapiddns_count = len(rd_subdomains)
                all_subdomains.update(rd_subdomains)
                logger.info("RapidDNS: Found %d subdomain(s)", len(rd_subdomains))
            except CRTReconError as exc:
                logger.warning("RapidDNS fetch failed: %s", exc)
            except Exception as exc:  # pragma: no cover
                logger.warning("Unexpected error during RapidDNS fetch: %s", exc)

    # ─── Validate we have results ────────────────────────────────────────────
    if not all_subdomains:
        error_msg = (
            f"No subdomains found for {config.domain} from any source. "
            "Ensure the domain is valid and has public certificates."
        )
        if not result.crtsh_available:
            error_msg += " (CRT.sh was unavailable during this scan)"
        result.error = error_msg
        result.elapsed = time.monotonic() - start
        return result

    # ─── Sort and prepare for export ─────────────────────────────────────────
    result.subdomains = sorted(all_subdomains)

    # ─── Probe subdomains (if enabled) ───────────────────────────────────────
    if config.probe:
        result.probe_results = probe_subdomains(result.subdomains, timeout=config.probe_timeout, workers=config.probe_workers)
        if config.alive_only:
            alive = {r.subdomain for r in result.probe_results if r.alive}
            result.subdomains = [s for s in result.subdomains if s in alive]

    # ─── Export results ─────────────────────────────────────────────────────
    if config.formats:
        metadata = {
            "cert_records_fetched": result.cert_count,
            "hackertarget_results": result.hackertarget_count,
            "rapiddns_results": result.rapiddns_count,
            "retries_configured": config.retries,
            "sources": (["crt.sh"] if result.crtsh_available else [])
            + (["hackertarget"] if config.use_hackertarget else [])
            + (["rapiddns"] if config.use_rapiddns else []),
            "crtsh_available": result.crtsh_available,
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