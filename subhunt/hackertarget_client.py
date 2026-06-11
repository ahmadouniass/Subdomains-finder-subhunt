"""
hackertarget_client.py — HackerTarget API client for subdomain enumeration.
"""

import time
import logging
from typing import Set

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import HackerTargetClientError

logger = logging.getLogger(__name__)

HACKERTARGET_BASE_URL = "https://api.hackertarget.com"
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
                "https://github.com/ahmadouniass/Subdomains-finder-crtsh)"
            ),
        }
    )
    return session


def _parse_response(text: str) -> list[str]:
    """
    Parse plain-text HackerTarget response into a list of subdomain strings.
    Each line has the format ``subdomain.example.com,1.2.3.4``.
    """
    subdomains: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 1)
        subdomain = parts[0].strip().lower()
        if subdomain:
            subdomains.append(subdomain)
    return subdomains


class HackerTargetClient:
    """
    Client responsible for querying the HackerTarget API for subdomain enumeration.

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

    def fetch_subdomains(self, domain: str) -> Set[str]:
        """
        Fetch subdomains for *domain* from HackerTarget API.

        Args:
            domain: The apex domain to query (e.g. ``example.com``).

        Returns:
            A set of subdomain strings.

        Raises:
            HackerTargetClientError: On HTTP error or network failure.
        """
        url = f"{HACKERTARGET_BASE_URL}/hostsearch/"
        params = {"q": domain}

        logger.debug("GET %s params=%s", url, params)
        start = time.monotonic()

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.ConnectionError as exc:
            raise HackerTargetClientError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise HackerTargetClientError(f"Request time out after {self.timeout}s: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise HackerTargetClientError(f"Unexpected request error: {exc}") from exc

        elapsed = time.monotonic() - start
        logger.debug(
            "Response: HTTP %s  (%.2fs)  %d bytes",
            response.status_code,
            elapsed,
            len(response.content),
        )

        if response.status_code == 404:
            logger.info("No records found for domain: %s", domain)
            return set()

        if response.status_code == 429:
            raise HackerTargetClientError("HackerTarget rate limit reached. Try again later.")

        if not response.ok:
            raise HackerTargetClientError(f"HackerTarget returned HTTP {response.status_code} for domain {domain}")

        # HackerTarget returns CSV-like format (domain,ip per line)
        # or "error" message if no results
        text = response.text.strip()
        if text.lower().startswith("error"):
            logger.info("HackerTarget returned error for %s: %s", domain, text)
            return set()

        subdomains = set(_parse_response(text))
        logger.info("Fetched %d subdomain(s) from HackerTarget for %s", len(subdomains), domain)
        return subdomains

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "HackerTargetClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
