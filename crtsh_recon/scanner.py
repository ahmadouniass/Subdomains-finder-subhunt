"""
scanner.py — High-level orchestrator that ties together client, parser and exporter.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .client import CRTClient
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


def run_scan(config: ScanConfig) -> ScanResult:
    """
    Execute a full subdomain enumeration scan for *config.domain*.

    Steps:
    1. Fetch raw certificate records via :class:`CRTClient`.
    2. Parse & deduplicate subdomains with :func:`extract_subdomains`.
    3. Export results in the requested formats.

    Args:
        config: A populated :class:`ScanConfig` instance.

    Returns:
        A :class:`ScanResult` with all findings and metadata.
    """
    result = ScanResult(domain=config.domain)
    start = time.monotonic()

    with CRTClient(
        timeout=config.timeout,
        retries=config.retries,
        backoff=config.backoff,
    ) as client:
        try:
            logger.debug("Starting scan for %s", config.domain)
            records = client.fetch_certificates(config.domain)
            result.cert_count = len(records)

            subdomains = extract_subdomains(records, config.domain)
            result.subdomains = subdomains

            if subdomains and config.formats:
                metadata = {
                    "cert_records_fetched": result.cert_count,
                    "retries_configured": config.retries,
                }
                result.exported_files = export_results(
                    subdomains=subdomains,
                    domain=config.domain,
                    formats=config.formats,
                    output_dir=config.output_dir,
                    metadata=metadata,
                )
            elif not subdomains:
                logger.info("No subdomains found — skipping export.")

        except CRTReconError as exc:
            logger.error("Scan failed: %s", exc)
            result.error = str(exc)
        except Exception as exc:  # pragma: no cover
            logger.exception("Unexpected error during scan: %s", exc)
            result.error = f"Unexpected error: {exc}"

    result.elapsed = time.monotonic() - start
    logger.debug("Scan completed in %.2fs", result.elapsed)
    return result
