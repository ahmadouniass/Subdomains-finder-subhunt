"""
tests/test_prober.py — Unit tests for subhunt.prober

All network calls are mocked via unittest.mock.patch so no real HTTP
requests are made during testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import ConnectionError, Timeout, RequestException

from subhunt.prober import ProbeResult, _probe_one, probe_subdomains


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DOMAIN = "example.com"
SUB1 = "api.example.com"
SUB2 = "mail.example.com"
SUB3 = "dead.example.com"


def _make_response(status_code: int, url: str, history=None) -> MagicMock:
    """Build a fake requests.Response-like mock."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.history = history or []
    return resp


# ---------------------------------------------------------------------------
# ProbeResult dataclass
# ---------------------------------------------------------------------------

class TestProbeResult:
    def test_default_fields(self):
        pr = ProbeResult(subdomain=SUB1)
        assert pr.subdomain == SUB1
        assert pr.alive is False
        assert pr.status_code is None
        assert pr.url is None
        assert pr.redirect_url is None
        assert pr.protocol is None
        assert pr.error is None

    def test_alive_result(self):
        pr = ProbeResult(
            subdomain=SUB1,
            alive=True,
            status_code=200,
            url=f"https://{SUB1}/",
            protocol="https",
        )
        assert pr.alive is True
        assert pr.status_code == 200
        assert pr.protocol == "https"

    def test_dead_result(self):
        pr = ProbeResult(subdomain=SUB1, alive=False, error="timeout")
        assert pr.alive is False
        assert pr.error == "timeout"


# ---------------------------------------------------------------------------
# _probe_one — single host probing
# ---------------------------------------------------------------------------

class TestProbeOne:
    @patch("subhunt.prober.requests.get")
    def test_alive_https(self, mock_get):
        """Should return alive=True when HTTPS responds."""
        mock_get.return_value = _make_response(200, f"https://{SUB1}/")
        result = _probe_one(SUB1, timeout=5)

        assert result.alive is True
        assert result.status_code == 200
        assert result.protocol == "https"
        assert result.subdomain == SUB1
        # Should only try HTTPS (got response on first try)
        assert mock_get.call_count == 1

    @patch("subhunt.prober.requests.get")
    def test_alive_http_fallback(self, mock_get):
        """Should fall back to HTTP when HTTPS fails."""
        mock_get.side_effect = [
            ConnectionError("HTTPS refused"),          # HTTPS fails
            _make_response(200, f"http://{SUB1}/"),    # HTTP succeeds
        ]
        result = _probe_one(SUB1, timeout=5)

        assert result.alive is True
        assert result.protocol == "http"
        assert mock_get.call_count == 2

    @patch("subhunt.prober.requests.get")
    def test_dead_both_protocols_fail(self, mock_get):
        """Should return alive=False when both HTTPS and HTTP fail."""
        mock_get.side_effect = ConnectionError("refused")
        result = _probe_one(SUB1, timeout=5)

        assert result.alive is False
        assert result.subdomain == SUB1
        assert result.error is not None
        assert mock_get.call_count == 2  # tried both protocols

    @patch("subhunt.prober.requests.get")
    def test_timeout_returns_dead(self, mock_get):
        """Timeout on both protocols → dead."""
        mock_get.side_effect = Timeout("timed out")
        result = _probe_one(SUB1, timeout=5)

        assert result.alive is False

    @patch("subhunt.prober.requests.get")
    def test_redirect_captured(self, mock_get):
        """Redirect URL is captured from response history."""
        redirect = MagicMock()
        redirect.headers = {"Location": "https://www.example.com/"}
        response = _make_response(200, "https://www.example.com/", history=[redirect])
        mock_get.return_value = response

        result = _probe_one(SUB1, timeout=5)

        assert result.alive is True
        assert result.redirect_url == "https://www.example.com/"

    @patch("subhunt.prober.requests.get")
    def test_no_redirect_when_no_history(self, mock_get):
        """redirect_url should be None when there's no redirect."""
        mock_get.return_value = _make_response(200, f"https://{SUB1}/")
        result = _probe_one(SUB1, timeout=5)

        assert result.redirect_url is None

    @patch("subhunt.prober.requests.get")
    def test_status_403_still_alive(self, mock_get):
        """A 403 response means the host is alive (just forbidden)."""
        mock_get.return_value = _make_response(403, f"https://{SUB1}/")
        result = _probe_one(SUB1, timeout=5)

        assert result.alive is True
        assert result.status_code == 403

    @patch("subhunt.prober.requests.get")
    def test_status_301_alive(self, mock_get):
        """A 301 redirect that resolves = alive."""
        mock_get.return_value = _make_response(301, f"https://{SUB1}/")
        result = _probe_one(SUB1, timeout=5)

        assert result.alive is True
        assert result.status_code == 301

    @patch("subhunt.prober.requests.get")
    def test_request_exception_dead(self, mock_get):
        """Generic RequestException → dead."""
        mock_get.side_effect = RequestException("generic error")
        result = _probe_one(SUB1, timeout=5)

        assert result.alive is False


# ---------------------------------------------------------------------------
# probe_subdomains — batch probing
# ---------------------------------------------------------------------------

class TestProbeSubdomains:
    def test_empty_list_returns_empty(self):
        results = probe_subdomains([])
        assert results == []

    @patch("subhunt.prober._probe_one")
    def test_returns_result_for_each_subdomain(self, mock_probe):
        """Should return one ProbeResult per subdomain."""
        mock_probe.side_effect = lambda sub, timeout: ProbeResult(
            subdomain=sub, alive=True, status_code=200
        )
        results = probe_subdomains([SUB1, SUB2], timeout=5, workers=2)

        assert len(results) == 2
        assert {r.subdomain for r in results} == {SUB1, SUB2}

    @patch("subhunt.prober._probe_one")
    def test_preserves_order(self, mock_probe):
        """Output order should match input order."""
        subs = [SUB1, SUB2, SUB3]
        mock_probe.side_effect = lambda sub, timeout: ProbeResult(subdomain=sub)
        results = probe_subdomains(subs, timeout=5, workers=3)

        assert [r.subdomain for r in results] == subs

    @patch("subhunt.prober._probe_one")
    def test_mixed_alive_dead(self, mock_probe):
        """Should handle mix of alive and dead results."""
        def _side(sub, timeout):
            return ProbeResult(subdomain=sub, alive=(sub == SUB1))

        mock_probe.side_effect = _side
        results = probe_subdomains([SUB1, SUB2], timeout=5, workers=2)

        alive = [r for r in results if r.alive]
        dead = [r for r in results if not r.alive]
        assert len(alive) == 1
        assert len(dead) == 1
        assert alive[0].subdomain == SUB1

    @patch("subhunt.prober.requests.get")
    def test_workers_parameter_respected(self, mock_get):
        """Should complete even with workers=1."""
        mock_get.return_value = _make_response(200, f"https://{SUB1}/")
        results = probe_subdomains([SUB1], timeout=5, workers=1)
        assert len(results) == 1
        assert results[0].alive is True

    @patch("subhunt.prober.requests.get")
    def test_all_dead_returns_full_list(self, mock_get):
        """Should still return results for all subdomains even when all dead."""
        mock_get.side_effect = ConnectionError("refused")
        results = probe_subdomains([SUB1, SUB2], timeout=5, workers=2)

        assert len(results) == 2
        assert all(not r.alive for r in results)

    @patch("subhunt.prober.requests.get")
    def test_urllib3_warnings_suppressed(self, mock_get):
        """Should suppress InsecureRequestWarning without raising."""
        mock_get.return_value = _make_response(200, f"https://{SUB1}/")
        # Should not raise even though verify=False is used
        results = probe_subdomains([SUB1], timeout=5, workers=1)
        assert len(results) == 1

    @patch("subhunt.prober._probe_one")
    def test_single_subdomain(self, mock_probe):
        """Edge case: single item list."""
        mock_probe.return_value = ProbeResult(subdomain=SUB1, alive=True, status_code=200)
        results = probe_subdomains([SUB1])
        assert len(results) == 1
        assert results[0].alive is True

    @patch("subhunt.prober._probe_one")
    def test_large_batch(self, mock_probe):
        """Should handle a large list (stress test with mocks)."""
        subs = [f"sub{i}.example.com" for i in range(50)]
        mock_probe.side_effect = lambda sub, timeout: ProbeResult(subdomain=sub, alive=True)
        results = probe_subdomains(subs, timeout=5, workers=10)
        assert len(results) == 50
        assert all(r.alive for r in results)


# ---------------------------------------------------------------------------
# Integration: probe_subdomains called via scanner
# ---------------------------------------------------------------------------

class TestProberIntegrationWithScanner:
    """Verify that scanner correctly passes probe results through."""

    @patch("subhunt.scanner.export_results")
    @patch("subhunt.scanner.probe_subdomains")
    @patch("subhunt.scanner.RapidDNSClient")
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_probe_enabled_populates_result(
        self, mock_crt, mock_ht, mock_rd, mock_probe, mock_export
    ):
        from subhunt.scanner import run_scan, ScanConfig

        # CRT setup
        crt_inst = mock_crt.return_value.__enter__.return_value
        crt_inst.health_check.return_value = True
        crt_inst.fetch_certificates.return_value = [
            {"name_value": SUB1, "common_name": DOMAIN}
        ]
        # Disable HackerTarget and RapidDNS
        mock_ht.return_value.__enter__.return_value.fetch_subdomains.return_value = set()
        mock_rd.return_value.__enter__.return_value.fetch_subdomains.return_value = set()

        # Probe mock
        mock_probe.return_value = [
            ProbeResult(subdomain=SUB1, alive=True, status_code=200)
        ]
        mock_export.return_value = {}

        config = ScanConfig(
            domain=DOMAIN,
            formats=[],
            output_dir="/tmp/test",
            probe=True,
            probe_timeout=3,
            probe_workers=5,
        )
        result = run_scan(config)

        assert result.alive_count == 1
        assert result.dead_count == 0
        assert len(result.probe_results) == 1
        mock_probe.assert_called_once()

    @patch("subhunt.scanner.export_results")
    @patch("subhunt.scanner.probe_subdomains")
    @patch("subhunt.scanner.RapidDNSClient")
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_alive_only_filters_subdomains(
        self, mock_crt, mock_ht, mock_rd, mock_probe, mock_export
    ):
        from subhunt.scanner import run_scan, ScanConfig

        crt_inst = mock_crt.return_value.__enter__.return_value
        crt_inst.health_check.return_value = True
        crt_inst.fetch_certificates.return_value = [
            {"name_value": f"{SUB1}\n{SUB2}", "common_name": DOMAIN}
        ]
        mock_ht.return_value.__enter__.return_value.fetch_subdomains.return_value = set()
        mock_rd.return_value.__enter__.return_value.fetch_subdomains.return_value = set()

        # Only SUB1 is alive
        mock_probe.return_value = [
            ProbeResult(subdomain=SUB1, alive=True, status_code=200),
            ProbeResult(subdomain=SUB2, alive=False),
        ]
        mock_export.return_value = {}

        config = ScanConfig(
            domain=DOMAIN,
            formats=[],
            output_dir="/tmp/test",
            probe=True,
            alive_only=True,
        )
        result = run_scan(config)

        assert result.subdomains == [SUB1]

    @patch("subhunt.scanner.export_results")
    @patch("subhunt.scanner.RapidDNSClient")
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_probe_disabled_skips_probing(
        self, mock_crt, mock_ht, mock_rd, mock_export
    ):
        from subhunt.scanner import run_scan, ScanConfig

        crt_inst = mock_crt.return_value.__enter__.return_value
        crt_inst.health_check.return_value = True
        crt_inst.fetch_certificates.return_value = [
            {"name_value": SUB1, "common_name": DOMAIN}
        ]
        mock_ht.return_value.__enter__.return_value.fetch_subdomains.return_value = set()
        mock_rd.return_value.__enter__.return_value.fetch_subdomains.return_value = set()
        mock_export.return_value = {}

        config = ScanConfig(domain=DOMAIN, formats=[], output_dir="/tmp/test", probe=False)
        result = run_scan(config)

        assert result.probe_results == []
        assert result.alive_count == 0
        assert result.dead_count == 0
