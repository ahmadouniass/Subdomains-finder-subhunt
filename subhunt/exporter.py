"""
exporter.py — Write subdomain results to TXT, JSON and CSV files.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .exceptions import ExportError

logger = logging.getLogger(__name__)


def _ensure_output_dir(directory: str) -> Path:
    """Create *directory* (and parents) if it does not exist."""
    path = Path(directory)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ExportError(f"Cannot create output directory {directory!r}: {exc}") from exc
    return path


def _timestamp() -> str:
    """Return a filesystem-safe UTC timestamp string."""
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_write(filepath: Path, content: str) -> None:
    """Write *content* to *filepath*, raising :class:`ExportError` on failure."""
    try:
        filepath.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Failed to write {filepath}: {exc}") from exc


# ---------------------------------------------------------------------------
# Per-format writers
# ---------------------------------------------------------------------------


def export_txt(
    subdomains: list[str],
    domain: str,
    output_dir: str,
    filename: Optional[str] = None,
) -> Path:
    """
    Export *subdomains* as a plain-text file (one subdomain per line).

    Args:
        subdomains: Sorted list of subdomain strings.
        domain:     Apex domain (used in the default filename).
        output_dir: Destination directory.
        filename:   Override the auto-generated filename.

    Returns:
        Path to the written file.
    """
    out_dir = _ensure_output_dir(output_dir)
    fname = filename or f"{domain}_{_timestamp()}.txt"
    filepath = out_dir / fname

    content = "\n".join(subdomains) + ("\n" if subdomains else "")
    _safe_write(filepath, content)

    logger.info("TXT exported → %s (%d entries)", filepath, len(subdomains))
    return filepath


def export_json(
    subdomains: list[str],
    domain: str,
    output_dir: str,
    filename: Optional[str] = None,
    metadata: Optional[dict] = None,
    probe_results: Optional[list] = None,
) -> Path:
    """
    Export *subdomains* as a structured JSON file.

    Args:
        subdomains:    Sorted list of subdomain strings.
        domain:        Apex domain.
        output_dir:    Destination directory.
        filename:      Override the auto-generated filename.
        metadata:      Optional dict of extra metadata to embed in the JSON.
        probe_results: Optional list of ProbeResult objects.

    Returns:
        Path to the written file.
    """
    out_dir = _ensure_output_dir(output_dir)
    fname = filename or f"{domain}_{_timestamp()}.json"
    filepath = out_dir / fname

    payload: dict = {
        "meta": {
            "domain": domain,
            "total": len(subdomains),
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "tool": "subhunt",
            **(metadata or {}),
        },
        "subdomains": subdomains,
    }

    if probe_results:
        payload["probe_results"] = [
            {
                "subdomain": p.subdomain,
                "alive": p.alive,
                "status_code": p.status_code,
                "url": p.url,
                "protocol": p.protocol,
            }
            for p in probe_results
        ]

    content = json.dumps(payload, indent=2, ensure_ascii=False)
    _safe_write(filepath, content)

    logger.info("JSON exported → %s (%d entries)", filepath, len(subdomains))
    return filepath


def export_csv(
    subdomains: list[str],
    domain: str,
    output_dir: str,
    filename: Optional[str] = None,
    probe_results: Optional[list] = None,
) -> Path:
    """
    Export *subdomains* as a CSV file.

    When *probe_results* is provided, extra columns (alive, status_code, url)
    are added to the output.

    Args:
        subdomains:    Sorted list of subdomain strings.
        domain:        Apex domain.
        output_dir:    Destination directory.
        filename:      Override the auto-generated filename.
        probe_results: Optional list of ProbeResult objects.

    Returns:
        Path to the written file.
    """
    out_dir = _ensure_output_dir(output_dir)
    fname = filename or f"{domain}_{_timestamp()}.csv"
    filepath = out_dir / fname

    # Build a probe lookup map for O(1) access
    probe_map = {p.subdomain: p for p in probe_results} if probe_results else {}

    try:
        with filepath.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if probe_map:
                writer.writerow(["#", "subdomain", "alive", "status_code", "url"])
                for idx, sub in enumerate(subdomains, start=1):
                    pr = probe_map.get(sub)
                    writer.writerow([
                        idx, sub,
                        pr.alive if pr else "",
                        pr.status_code if pr else "",
                        pr.url if pr else "",
                    ])
            else:
                writer.writerow(["#", "subdomain"])
                for idx, sub in enumerate(subdomains, start=1):
                    writer.writerow([idx, sub])
    except OSError as exc:
        raise ExportError(f"Failed to write CSV {filepath}: {exc}") from exc

    logger.info("CSV exported → %s (%d entries)", filepath, len(subdomains))
    return filepath


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def export_results(
    subdomains: list[str],
    domain: str,
    formats: list[str],
    output_dir: str = "output",
    metadata: Optional[dict] = None,
    probe_results: Optional[list] = None,
) -> dict[str, Path]:
    """
    Export *subdomains* in every requested format.

    Args:
        subdomains:    Sorted list of subdomain strings.
        domain:        Apex domain.
        formats:       List of format identifiers (``"txt"``, ``"json"``, ``"csv"``).
        output_dir:    Destination directory.
        metadata:      Optional extra metadata for the JSON export.
        probe_results: Optional list of ProbeResult for enriched CSV/JSON export.

    Returns:
        Mapping of format identifier → written file path.

    Raises:
        ExportError: If any write operation fails.
    """
    written: dict[str, Path] = {}

    _dispatchers = {
        "txt": lambda: export_txt(subdomains, domain, output_dir),
        "json": lambda: export_json(
            subdomains, domain, output_dir, metadata=metadata, probe_results=probe_results
        ),
        "csv": lambda: export_csv(subdomains, domain, output_dir, probe_results=probe_results),
    }

    for fmt in formats:
        if fmt not in _dispatchers:
            logger.warning("Unknown export format %r — skipping.", fmt)
            continue
        written[fmt] = _dispatchers[fmt]()

    return written
