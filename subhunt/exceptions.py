"""
exceptions.py — Custom exception hierarchy for crtsh-recon.
"""


class CRTReconError(Exception):
    """Base exception for crtsh-recon."""

    pass


class CRTClientError(CRTReconError):
    """Raised when CRT.sh API client encounters an error."""

    pass


class CRTNotFoundError(CRTClientError):
    """Raised when CRT.sh returns 404 (no records found)."""

    pass


class CRTRateLimitError(CRTClientError):
    """Raised when CRT.sh returns 429 (rate limited)."""

    pass


class HackerTargetClientError(CRTReconError):
    """Raised when HackerTarget API client encounters an error."""

    pass


class ValidationError(CRTReconError):
    """Raised when input validation fails."""

    pass


class ExportError(CRTReconError):
    """Raised when result export fails."""

    pass
