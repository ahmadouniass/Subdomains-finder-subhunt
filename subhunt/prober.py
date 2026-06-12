"""
prober.py — Concurrent HTTP/HTTPS probing for discovered subdomains.

For each subdomain, tries HTTPS first then falls back to HTTP.
Uses a ThreadPoolExecutor for parallelism so probing 100+ hosts
stays fast (default: 20 workers).

Usage::

    from subhunt.prober import probe_subdomains

    results = probe_subdomains(["api.example.com", "mail.example.com"], timeout=5)
    for r in results:
        print(r.subdomain, "ALIVE" if r.alive else "DEAD", r.status_code)
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

# Protocols tried in order — HTTPS first, HTTP as fallback.
_PROTOCOLS = ("https", "http")

# Browser-like UA to avoid being blocked by simple filters.
_USER_AGENT = "Mozilla/5.0 (compatible; subhunt/1.4.0; +https://github.com/ahmadouniass/Subdomains-finder-subhunt)"


@dataclass
class ProbeResult:
    """Result of a single HTTP probe attempt."""

    subdomain: str
    alive: bool = False
    status_code: Optional[int] = None
    url: Optional[str] = None  # final URL after redirects
    redirect_url: Optional[str] = None  # first redirect location (if any)
    protocol: Optional[str] = None  # "https" or "http"
    error: Optional[str] = None


def _probe_one(subdomain: str, timeout: int) -> ProbeResult:
    """
    Try to reach *subdomain* over HTTPS then HTTP.

    Args:
        subdomain: Hostname to probe (no scheme).
        timeout:   Per-request timeout in seconds.

    Returns:
        A populated :class:`ProbeResult`.
    """
    headers = {"User-Agent": _USER_AGENT}

    for proto in _PROTOCOLS:
        url = f"{proto}://{subdomain}"
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers=headers,
                verify=False,  # many subdomains have self-signed certs
            )
            redirect_url = None
            if resp.history:
                redirect_url = resp.history[0].headers.get("Location")

            logger.debug("ALIVE %s  [%d]  final=%s", subdomain, resp.status_code, resp.url)
            return ProbeResult(
                subdomain=subdomain,
                alive=True,
                status_code=resp.status_code,
                url=resp.url,
                redirect_url=redirect_url,
                protocol=proto,
            )

        except RequestException as exc:
            logger.debug("DEAD  %s (%s): %s", subdomain, proto, exc)
            # Try next protocol before giving up.
            continue

    return ProbeResult(
        subdomain=subdomain,
        alive=False,
        error="No response on HTTPS or HTTP",
    )


def probe_subdomains(
    subdomains: list[str],
    timeout: int = 5,
    workers: int = 20,
) -> list[ProbeResult]:
    """
    Probe a list of subdomains concurrently.

    Args:
        subdomains: List of hostnames to probe.
        timeout:    Per-request timeout in seconds (default: 5).
        workers:    Maximum concurrent threads (default: 20).

    Returns:
        List of :class:`ProbeResult` objects, in the same order as *subdomains*.
    """
    if not subdomains:
        return []

    # Suppress InsecureRequestWarning from urllib3 (verify=False above).
    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

    results: dict[str, ProbeResult] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_sub = {executor.submit(_probe_one, sub, timeout): sub for sub in subdomains}
        for future in as_completed(future_to_sub):
            sub = future_to_sub[future]
            try:
                results[sub] = future.result()
            except Exception as exc:  # pragma: no cover
                logger.warning("Unexpected probe error for %s: %s", sub, exc)
                results[sub] = ProbeResult(subdomain=sub, alive=False, error=str(exc))

    # Preserve original order.
    return [results[sub] for sub in subdomains if sub in results]
