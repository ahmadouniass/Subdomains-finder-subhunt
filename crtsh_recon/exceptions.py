"""
exceptions.py — Custom exception hierarchy for crtsh-recon.
"""


class CRTReconError(Exception):
    """Base exception for all crtsh-recon errors."""


class CRTClientError(CRTReconError):
    """Raised when the HTTP client encounters an unrecoverable error."""


class CRTNotFoundError(CRTClientError):
    """Raised when crt.sh returns no records for the given domain."""


class CRTRateLimitError(CRTClientError):
    """Raised when crt.sh rate-limits the client."""


class ValidationError(CRTReconError):
    """Raised when input validation fails."""


class ExportError(CRTReconError):
    """Raised when writing results to disk fails."""
