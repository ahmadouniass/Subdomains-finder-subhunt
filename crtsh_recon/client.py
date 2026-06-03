"""
client.py — CRT.sh HTTP client with retry logic and timeout handling.
"""

import time
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import CRTClientError, CRTRateLimitError, CRTNotFoundError

logger = logging.getLogger(__name__)

CRTSH_BASE_URL = "https://crt.sh"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 2.0


def _build_session(retries: int, backoff: float) -> requests.Session:
    """Build a requests.Session with retry strategy."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": (
                "crtsh-recon/1.0.0 (OSINT Subdomain Enumeration Tool; "
                "https://github.com/ahmadouniass/Cyber-tools)"
            ),
            "Accept": "application/json",
        }
    )
    return session


class CRTClient:
    """
    Client responsible for querying the crt.sh certificate transparency API.

    Args:
        timeout: Request timeout in seconds.
        retries: Number of retry attempts on transient failures.
        backoff: Exponential backoff factor between retries.
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff: float = DEFAULT_BACKOFF,
    ) -> None:
        self.timeout = timeout
        self.session = _build_session(retries, backoff)

    def fetch_certificates(self, domain: str) -> list[dict]:
        """
        Fetch all certificate records for *domain* from crt.sh.

        Args:
            domain: The apex domain to query (e.g. ``example.com``).

        Returns:
            A list of raw certificate record dicts from the JSON response.

        Raises:
            CRTNotFoundError: If crt.sh returns HTTP 404.
            CRTRateLimitError: If crt.sh returns HTTP 429.
            CRTClientError: On any other HTTP error or network failure.
        """
        url = CRTSH_BASE_URL
        params = {"q": f"%.{domain}", "output": "json"}

        logger.debug("GET %s params=%s", url, params)
        start = time.monotonic()

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.ConnectionError as exc:
            raise CRTClientError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise CRTClientError(f"Request timed out after {self.timeout}s: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise CRTClientError(f"Unexpected request error: {exc}") from exc

        elapsed = time.monotonic() - start
        logger.debug(
            "Response: HTTP %s  (%.2fs)  %d bytes",
            response.status_code,
            elapsed,
            len(response.content),
        )

        if response.status_code == 404:
            raise CRTNotFoundError(f"No records found for domain: {domain}")
        if response.status_code == 429:
            raise CRTRateLimitError("crt.sh rate limit reached. Try again later.")
        if not response.ok:
            raise CRTClientError(f"crt.sh returned HTTP {response.status_code} for domain {domain}")

        try:
            data = response.json()
        except ValueError as exc:
            raise CRTClientError(
                f"Failed to parse JSON response: {exc}. "
                f"Raw (first 500 chars): {response.text[:500]}"
            ) from exc

        if not isinstance(data, list):
            raise CRTClientError(
                f"Unexpected JSON structure (expected list, got {type(data).__name__})"
            )

        logger.debug("Received %d certificate records", len(data))
        return data

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "CRTClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
