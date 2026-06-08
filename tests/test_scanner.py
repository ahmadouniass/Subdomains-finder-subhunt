"""
tests/test_scanner.py — Unit tests for crtsh_recon.scanner

All network calls mocked. Covers the new multi-source architecture:
health check, crtsh fetch, hackertarget fetch, merge, export, error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from subhunt.scanner import run_scan, ScanConfig, ScanResult
from subhunt.exceptions import CRTClientError, CRTNotFoundError, CRTRateLimitError, HackerTargetClientError, CRTReconError, RapidDNSClientError


# ─── Fixtures & helpers ───────────────────────────────────────────────────────

DOMAIN = "example.com"
CRTSH_SUBS = ["api.example.com", "mail.example.com"]
HT_SUBS = {"www.example.com", "vpn.example.com"}
RD_SUBS = {"rapiddns.example.com", "dns.example.com"}
ALL_SUBS = sorted(set(CRTSH_SUBS) | HT_SUBS | RD_SUBS)

FAKE_RECORDS = [
    {"name_value": "api.example.com\nmail.example.com", "common_name": "example.com"},
]


def _make_config(**kwargs) -> ScanConfig:
    defaults = dict(
        domain=DOMAIN,
        formats=["txt"],
        output_dir="/tmp/scanner_test_out",
        timeout=5,
        retries=1,
        backoff=0.0,
        use_hackertarget=True,
        use_rapiddns=False,
    )
    defaults.update(kwargs)
    return ScanConfig(**defaults)


def _mock_crt_client(healthy=True, records=None, side_effect=None):
    """Return a MagicMock that mimics CRTClient as context manager."""
    mock = MagicMock()
    instance = mock.return_value.__enter__.return_value
    instance.health_check.return_value = healthy
    if side_effect:
        instance.fetch_certificates.side_effect = side_effect
    else:
        instance.fetch_certificates.return_value = records or FAKE_RECORDS
    return mock


def _mock_ht_client(subdomains=None, side_effect=None):
    """Return a MagicMock that mimics HackerTargetClient as context manager."""
    mock = MagicMock()
    instance = mock.return_value.__enter__.return_value
    if side_effect:
        instance.fetch_subdomains.side_effect = side_effect
    else:
        instance.fetch_subdomains.return_value = subdomains if subdomains is not None else HT_SUBS
    return mock


def _mock_rd_client(subdomains=None, side_effect=None):
    """Return a MagicMock that mimics RapidDNSClient as context manager."""
    mock = MagicMock()
    instance = mock.return_value.__enter__.return_value
    if side_effect:
        instance.fetch_subdomains.side_effect = side_effect
    else:
        instance.fetch_subdomains.return_value = subdomains if subdomains is not None else RD_SUBS
    return mock


# ─── ScanConfig ───────────────────────────────────────────────────────────────

class TestScanConfig:
    def test_default_formats(self):
        assert ScanConfig(domain=DOMAIN).formats == ["txt"]

    def test_default_output_dir(self):
        assert ScanConfig(domain=DOMAIN).output_dir == "output"

    def test_hackertarget_enabled_by_default(self):
        assert ScanConfig(domain=DOMAIN).use_hackertarget is True

    def test_rapiddns_enabled_by_default(self):
        assert ScanConfig(domain=DOMAIN).use_rapiddns is True

    def test_custom_values(self):
        cfg = ScanConfig(domain=DOMAIN, formats=["json"], timeout=60, use_hackertarget=False, use_rapiddns=False)
        assert cfg.formats == ["json"]
        assert cfg.timeout == 60
        assert cfg.use_hackertarget is False


# ─── ScanResult ───────────────────────────────────────────────────────────────

class TestScanResult:
    def test_success_when_no_error(self):
        assert ScanResult(domain=DOMAIN).success is True

    def test_failure_when_error_set(self):
        assert ScanResult(domain=DOMAIN, error="fail").success is False

    def test_defaults(self):
        r = ScanResult(domain=DOMAIN)
        assert r.subdomains == []
        assert r.cert_count == 0
        assert r.hackertarget_count == 0
        assert r.rapiddns_count == 0
        assert r.exported_files == {}
        assert r.elapsed == 0.0
        assert r.crtsh_available is True


# ─── Happy path — both sources ────────────────────────────────────────────────

class TestRunScanBothSources:
    @patch("subhunt.scanner.export_results", return_value={"txt": Path("/tmp/out.txt")})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_success_returns_scan_result(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.side_effect = [_mock_crt_client().return_value, _mock_crt_client().return_value]
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config())
        assert isinstance(result, ScanResult)
        assert result.success is True

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_subdomains_merged_from_both_sources(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config())
        for sub in CRTSH_SUBS:
            assert sub in result.subdomains
        for sub in HT_SUBS:
            assert sub in result.subdomains

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_subdomains_deduplicated(self, MockCRT, MockHT, mock_extract, mock_export):
        # Both sources return same subdomain
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client(subdomains={"api.example.com"}).return_value

        result = run_scan(_make_config())
        assert result.subdomains.count("api.example.com") == 1

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_subdomains_sorted(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config())
        assert result.subdomains == sorted(result.subdomains)

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_cert_count_set(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client(records=FAKE_RECORDS).return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config())
        assert result.cert_count == len(FAKE_RECORDS)

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_hackertarget_count_set(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client(subdomains=HT_SUBS).return_value

        result = run_scan(_make_config())
        assert result.hackertarget_count == len(HT_SUBS)

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_elapsed_set(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config())
        assert result.elapsed >= 0.0

    @patch("subhunt.scanner.export_results", return_value={"txt": Path("/tmp/out.txt")})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_exported_files_populated(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config(formats=["txt"]))
        assert "txt" in result.exported_files


# ─── crtsh_available flag ─────────────────────────────────────────────────────

class TestCrtshAvailability:
    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=[])
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_crtsh_available_true_when_healthy(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client(healthy=True).return_value
        MockHT.return_value = _mock_ht_client(subdomains=HT_SUBS).return_value

        result = run_scan(_make_config())
        assert result.crtsh_available is True

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_crtsh_available_false_when_unhealthy(self, MockCRT, MockHT, mock_export):
        MockCRT.return_value = _mock_crt_client(healthy=False).return_value
        MockHT.return_value = _mock_ht_client(subdomains=HT_SUBS).return_value

        result = run_scan(_make_config())
        assert result.crtsh_available is False

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_crtsh_down_uses_hackertarget_as_fallback(self, MockCRT, MockHT, mock_export):
        MockCRT.return_value = _mock_crt_client(healthy=False).return_value
        MockHT.return_value = _mock_ht_client(subdomains=HT_SUBS).return_value

        result = run_scan(_make_config())
        assert result.success is True
        for sub in HT_SUBS:
            assert sub in result.subdomains

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_crtsh_down_error_mentions_unavailability(self, MockCRT, MockHT, mock_export):
        MockCRT.return_value = _mock_crt_client(healthy=False).return_value
        MockHT.return_value = _mock_ht_client(subdomains=set()).return_value

        result = run_scan(_make_config())
        assert result.success is False
        assert "unavailable" in result.error.lower()


# ─── HackerTarget disabled ────────────────────────────────────────────────────

class TestHackerTargetDisabled:
    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_hackertarget_not_called_when_disabled(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value

        run_scan(_make_config(use_hackertarget=False))
        MockHT.assert_not_called()

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_crtsh_only_results_when_ht_disabled(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value

        result = run_scan(_make_config(use_hackertarget=False))
        assert result.success is True
        assert result.hackertarget_count == 0


# ─── Error handling ───────────────────────────────────────────────────────────

class TestRunScanErrors:
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_no_results_from_any_source_sets_error(self, MockCRT, MockHT):
        MockCRT.return_value = _mock_crt_client(records=[]).return_value
        MockHT.return_value = _mock_ht_client(subdomains=set()).return_value

        with patch("subhunt.scanner.extract_subdomains", return_value=[]):
            result = run_scan(_make_config())

        assert result.success is False
        assert result.error is not None

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_crtsh_error_continues_to_hackertarget(self, MockCRT, MockHT, mock_export):
        MockCRT.return_value = _mock_crt_client(
            side_effect=CRTClientError("502 bad gateway")
        ).return_value
        MockHT.return_value = _mock_ht_client(subdomains=HT_SUBS).return_value

        result = run_scan(_make_config())
        assert result.success is True
        for sub in HT_SUBS:
            assert sub in result.subdomains

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_hackertarget_error_does_not_fail_scan(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client(
            side_effect=HackerTargetClientError("rate limited")
        ).return_value

        result = run_scan(_make_config())
        assert result.success is True
        for sub in CRTSH_SUBS:
            assert sub in result.subdomains

    @patch("subhunt.scanner.export_results", side_effect=CRTReconError("disk full"))
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_export_error_captured(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config())
        assert result.success is False

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_elapsed_set_even_on_error(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client(
            side_effect=CRTClientError("fail")
        ).return_value
        MockHT.return_value = _mock_ht_client(subdomains=set()).return_value

        result = run_scan(_make_config())
        assert result.elapsed >= 0.0

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_formats_empty_skips_export(self, MockCRT, MockHT, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config(formats=[]))
        mock_export.assert_not_called()
        assert result.success is True


class TestRapidDNSIntegration:
    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.RapidDNSClient")
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_rapiddns_enabled_merges_subdomains(self, MockCRT, MockHT, MockRD, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value
        MockRD.return_value = _mock_rd_client(subdomains={"rapiddns.example.com"}).return_value

        result = run_scan(_make_config(use_rapiddns=True))
        assert result.success is True
        assert "rapiddns.example.com" in result.subdomains
        assert result.rapiddns_count == 1

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.RapidDNSClient")
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_rapiddns_disabled_not_called(self, MockCRT, MockHT, MockRD, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value

        result = run_scan(_make_config(use_rapiddns=False))
        MockRD.assert_not_called()
        assert result.rapiddns_count == 0

    @patch("subhunt.scanner.export_results", return_value={})
    @patch("subhunt.scanner.extract_subdomains", return_value=CRTSH_SUBS)
    @patch("subhunt.scanner.RapidDNSClient")
    @patch("subhunt.scanner.HackerTargetClient")
    @patch("subhunt.scanner.CRTClient")
    def test_rapiddns_error_does_not_fail_scan(self, MockCRT, MockHT, MockRD, mock_extract, mock_export):
        MockCRT.return_value = _mock_crt_client().return_value
        MockHT.return_value = _mock_ht_client().return_value
        MockRD.return_value = _mock_rd_client(
            side_effect=RapidDNSClientError("scraping error")
        ).return_value

        result = run_scan(_make_config(use_rapiddns=True))
        assert result.success is True
        assert result.rapiddns_count == 0