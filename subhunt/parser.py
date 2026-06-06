"""
parser.py — Extract, clean and deduplicate subdomains from crt.sh records.
"""

import re
import logging
from typing import Iterator

logger = logging.getLogger(__name__)

# Matches a valid (sub)domain label: letters, digits, hyphens.
# Full domain: one or more labels separated by dots.
_DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")


def _split_name_value(raw: str) -> Iterator[str]:
    """
    crt.sh sometimes packs multiple names into a single ``name_value``
    field separated by newlines or spaces.  Yield each token individually.
    """
    for token in re.split(r"[\n\r\s]+", raw):
        yield token.strip()


def _strip_wildcard(name: str) -> str:
    """Remove leading wildcard prefix (``*.`` or ``%.``)."""
    if name.startswith("*.") or name.startswith("%."):
        return name[2:]
    return name


def _is_valid_subdomain(name: str, apex: str) -> bool:
    """
    Return True only when *name* is a syntactically valid FQDN that
    belongs to (or equals) *apex*.
    """
    if not name:
        return False
    if not _DOMAIN_RE.match(name):
        return False
    # Must end with the apex domain (prevents cross-domain pollution)
    if name != apex and not name.endswith(f".{apex}"):
        return False
    return True


def extract_subdomains(records: list[dict], domain: str) -> list[str]:
    """
    Parse raw crt.sh certificate records and return a sorted, deduplicated
    list of valid subdomains for *domain*.

    Args:
        records: List of cert record dicts as returned by :class:`CRTClient`.
        domain:  The apex domain used to filter results.

    Returns:
        Sorted list of unique subdomain strings.
    """
    apex = domain.lower().strip()
    seen: set[str] = set()

    for record in records:
        name_value: str = record.get("name_value", "")
        common_name: str = record.get("common_name", "")

        for raw_name in [name_value, common_name]:
            for token in _split_name_value(raw_name):
                cleaned = _strip_wildcard(token).lower()
                if cleaned in seen:
                    continue
                if _is_valid_subdomain(cleaned, apex):
                    seen.add(cleaned)
                else:
                    if cleaned:
                        logger.debug("Discarding invalid/out-of-scope name: %r", cleaned)

    subdomains = sorted(seen)
    logger.info(
        "Extracted %d unique subdomain(s) from %d certificate record(s)",
        len(subdomains),
        len(records),
    )
    return subdomains
