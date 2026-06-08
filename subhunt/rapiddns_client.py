"""
rapiddns_client.py — RapidDNS scraper for subdomain enumeration.

Endpoint: https://rapiddns.io/subdomain/{domain}?full=1

RapidDNS does not provide a public JSON API — this module scrapes the HTML
table returned by the website. The page contains a <table> with one subdomain
per row in the first column.

Rate limits: no official limit documented; be respectful with retries.
"""

import logging
import time

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import RapidDNSClientError

logger = logging.getLogger(__name__)

RAPIDDNS_BASE_URL = "https://rapiddns.io/subdomain"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 2.0

_ERROR_MARKERS = (
    "no result",
    "not found",
    "no records",
)


def _build_session(retries: int, backoff: float) -> requests.Session:
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
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )
    return session


def _parse_html(html: str) -> list[str]:
    """
    Parse RapidDNS HTML page and extract subdomains from the results table.

    The page contains a <table> where each <tr> has the subdomain in the
    first <td>. Rows without a valid subdomain are silently skipped.

    Args:
        html: Raw HTML response body.

    Returns:
        List of subdomain strings (may contain duplicates).
    """
    subdomains: list[str] = []

    try:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            logger.debug("[RapidDNS] No table found in HTML response")
            return []

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            subdomain = cells[0].get_text(strip=True).lower()
            if subdomain:
                subdomains.append(subdomain)

    except Exception as exc:
        logger.warning("[RapidDNS] HTML parsing error: %s", exc)

    return subdomains


class RapidDNSClient:
    """
    Client for scraping subdomain data from rapiddns.io.

    Args:
        timeout:  Request timeout in seconds.
        retries:  Number of retry attempts on transient failures.
        backoff:  Exponential back-off factor between retries.
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff: float = DEFAULT_BACKOFF,
    ) -> None:
        self.timeout = timeout
        self.session = _build_session(retries, backoff)

    def fetch_subdomains(self, domain: str) -> set[str]:
        """
        Scrape RapidDNS for known subdomains of *domain*.

        Args:
            domain: Apex domain to query (e.g. ``example.com``).

        Returns:
            Set of subdomain strings.

        Raises:
            RapidDNSClientError: On network errors or unexpected responses.
        """
        url = f"{RAPIDDNS_BASE_URL}/{domain}"
        params = {"full": "1"}

        logger.debug("GET %s params=%s", url, params)
        start = time.monotonic()

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.ConnectionError as exc:
            raise RapidDNSClientError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise RapidDNSClientError(f"Request timed out after {self.timeout}s") from exc
        except requests.exceptions.RequestException as exc:
            raise RapidDNSClientError(f"Unexpected request error: {exc}") from exc

        elapsed = time.monotonic() - start
        logger.debug("[RapidDNS] HTTP %s (%.2fs)", response.status_code, elapsed)

        if response.status_code == 429:
            raise RapidDNSClientError("[RapidDNS] Rate limited. Wait before retrying.")

        if not response.ok:
            raise RapidDNSClientError(f"[RapidDNS] HTTP {response.status_code} for domain {domain}")

        # Check for soft error messages in the page body
        body_lower = response.text.lower()
        for marker in _ERROR_MARKERS:
            if marker in body_lower:
                logger.info("[RapidDNS] No results for %s", domain)
                return set()

        subdomains = set(_parse_html(response.text))
        logger.info("[RapidDNS] Found %d subdomain(s) for %s", len(subdomains), domain)
        return subdomains

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "RapidDNSClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
