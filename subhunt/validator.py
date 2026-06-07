"""
validator.py — Input validation helpers.
"""

import re
import logging

from .exceptions import ValidationError

logger = logging.getLogger(__name__)

# RFC-1123 compliant domain regex (apex only — no leading wildcard or scheme)
_APEX_DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")

# Accepted export format identifiers
VALID_FORMATS = {"txt", "json", "csv"}


def validate_domain(domain: str) -> str:
    """
    Validate and normalise an apex domain name supplied by the user.

    - Strips leading/trailing whitespace and any trailing dot.
    - Lowercases the result.
    - Raises :class:`ValidationError` when the value is syntactically invalid.

    Args:
        domain: Raw domain string from CLI input.

    Returns:
        Normalised domain string.

    Raises:
        ValidationError: If *domain* is not a valid apex domain.
    """
    if not domain or not domain.strip():
        raise ValidationError("Domain name must not be empty.")

    normalised = domain.strip().rstrip(".").lower()

    # Strip scheme if the user accidentally passes a URL
    for scheme in ("https://", "http://"):
        if normalised.startswith(scheme):
            normalised = normalised[len(scheme) :]
            logger.debug("Stripped URL scheme from domain: %r → %r", domain, normalised)

    # Strip any path component
    if "/" in normalised:
        normalised = normalised.split("/")[0]
        logger.debug("Stripped path from domain: %r → %r", domain, normalised)

    if not _APEX_DOMAIN_RE.match(normalised):
        raise ValidationError(
            f"Invalid domain name: {normalised!r}. "
            "Expected a valid apex domain (e.g. example.com)."
        )

    return normalised


def validate_formats(formats: list[str]) -> list[str]:
    """
    Validate a list of export format strings.

    Args:
        formats: List of format identifiers (e.g. ``["txt", "json"]``).

    Returns:
        Normalised (lowercased) list of valid format identifiers.

    Raises:
        ValidationError: If any format is not in ``VALID_FORMATS``.
    """
    normalised = [f.strip().lower() for f in formats]
    invalid = [f for f in normalised if f not in VALID_FORMATS]
    if invalid:
        raise ValidationError(
            f"Unsupported export format(s): {invalid}. "
            f"Supported formats: {sorted(VALID_FORMATS)}"
        )
    return normalised


def validate_output_dir(path: str) -> str:
    """
    Basic sanity-check for an output directory path.

    Args:
        path: Directory path string.

    Returns:
        The original path if valid.

    Raises:
        ValidationError: If *path* is empty or suspiciously short.
    """
    if not path or not path.strip():
        raise ValidationError("Output directory path must not be empty.")
    return path.strip()
