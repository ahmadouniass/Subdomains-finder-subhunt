"""
subhunt — Professional subdomain enumeration via Certificate Transparency logs.

Usage (library)::

    from subhunt.scanner import run_scan, ScanConfig

    config = ScanConfig(domain="example.com", formats=["txt", "json", "csv"])
    result = run_scan(config)
    print(result.subdomains)
"""

__version__ = "1.2.0"
__author__ = "Ahmadou Niass"
__license__ = "MIT"

from .scanner import run_scan, ScanConfig, ScanResult  # noqa: F401
from .exceptions import (  # noqa: F401
    CRTReconError,
    CRTClientError,
    CRTNotFoundError,
    CRTRateLimitError,
    ValidationError,
    ExportError,
    RapidDNSClientError,
)
