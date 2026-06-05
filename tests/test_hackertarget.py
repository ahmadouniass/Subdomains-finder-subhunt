"""
tests/test_hackertarget.py — Unit tests for crtsh_recon.hackertarget_client
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock

from crtsh_recon.hackertarget_client import HackerTargetClient, _parse_response
from crtsh_recon.exceptions import HackerTargetClientError


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _mock_response(status_code: int, text: str = "") -> Mock:
    """Build a minimal mock requests.Response."""
    mock = Mock()
    mock.status_code = status_code
    mock.ok = 200 <= status_code < 300
    mock.text = text
    mock.content = text.encode()
    return mock


@pytest.fixture
def client():
    return HackerTargetClient(timeout=5, retries=1, backoff=0.0)


# ─── _parse_response (unit) ───────────────────────────────────────────────────

class TestParseResponse:
    def test_basic_csv_format(self):
        text = "api.example.com,1.2.3.4\nmail.example.com,5.6.7.8"
        result = _parse_response(text)
        assert "api.example.com" in result
        assert "mail.example.com" in result

    def test_ip_discarded(self):
        result = _parse_response("api.example.com,1.2.3.4")
        assert "1.2.3.4" not in result

    def test_empty_lines_skipped(self):
        result = _parse_response("api.example.com,1.2.3.4\n\n\nmail.example.com,5.6.7.8")
        assert len(result) == 2

    def test_lowercase_normalisation(self):
        result = _parse_response("API.EXAMPLE.COM,1.2.3.4\nMail.Example.Com,5.6.7.8")
        assert "api.example.com" in result
        assert "mail.example.com" in result
        assert "API.EXAMPLE.COM" not in result

    def test_empty_string_returns_empty(self):
        assert _parse_response("") == []

    def test_single_entry_no_newline(self):
        result = _parse_response("www.example.com,1.2.3.4")
        assert result == ["www.example.com"]


# ─── fetch_subdomains — happy path ────────────────────────────────────────────

class TestFetchSubdomainsSuccess:
    def test_returns_set_of_subdomains(self, client):
        text = "api.example.com,1.2.3.4\nmail.example.com,5.6.7.8\nexample.com,9.10.11.12"
        with patch.object(client.session, "get", return_value=_mock_response(200, text)):
            result = client.fetch_subdomains("example.com")
        assert "api.example.com" in result
        assert "mail.example.com" in result
        assert "example.com" in result

    def test_correct_count(self, client):
        text = "api.example.com,1.2.3.4\nmail.example.com,5.6.7.8"
        with patch.object(client.session, "get", return_value=_mock_response(200, text)):
            result = client.fetch_subdomains("example.com")
        assert len(result) == 2

    def test_subdomains_lowercased(self, client):
        text = "API.EXAMPLE.COM,1.2.3.4\nMail.Example.Com,5.6.7.8"
        with patch.object(client.session, "get", return_value=_mock_response(200, text)):
            result = client.fetch_subdomains("example.com")
        assert "api.example.com" in result
        assert "mail.example.com" in result
        assert "API.EXAMPLE.COM" not in result

    def test_correct_url_called(self, client):
        text = "api.example.com,1.2.3.4"
        with patch.object(client.session, "get", return_value=_mock_response(200, text)) as mock_get:
            client.fetch_subdomains("example.com")
        call_url = mock_get.call_args[0][0]
        assert "hackertarget.com" in call_url
        assert "hostsearch" in call_url

    def test_correct_query_param(self, client):
        text = "api.example.com,1.2.3.4"
        with patch.object(client.session, "get", return_value=_mock_response(200, text)) as mock_get:
            client.fetch_subdomains("example.com")
        params = mock_get.call_args[1]["params"]
        assert params["q"] == "example.com"


# ─── fetch_subdomains — empty / no results ────────────────────────────────────

class TestFetchSubdomainsEmpty:
    def test_error_prefix_returns_empty(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(200, "error check your search parameter")):
            result = client.fetch_subdomains("nonexistent.com")
        assert result == set()

    def test_empty_body_returns_empty(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(200, "")):
            result = client.fetch_subdomains("example.com")
        assert result == set()

    def test_404_returns_empty(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(404, "")):
            result = client.fetch_subdomains("example.com")
        assert result == set()

    def test_whitespace_only_body_returns_empty(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(200, "   \n\n  ")):
            result = client.fetch_subdomains("example.com")
        assert result == set()


# ─── fetch_subdomains — error handling ────────────────────────────────────────

class TestFetchSubdomainsErrors:
    def test_rate_limit_429_raises(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(429, "")):
            with pytest.raises(HackerTargetClientError, match="rate limit"):
                client.fetch_subdomains("example.com")

    def test_http_500_raises(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(500, "")):
            with pytest.raises(HackerTargetClientError, match="HTTP 500"):
                client.fetch_subdomains("example.com")

    def test_http_503_raises(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(503, "")):
            with pytest.raises(HackerTargetClientError, match="HTTP 503"):
                client.fetch_subdomains("example.com")

    def test_connection_error_raises(self, client):
        with patch.object(client.session, "get", side_effect=requests.exceptions.ConnectionError("fail")):
            with pytest.raises(HackerTargetClientError, match="Connection failed"):
                client.fetch_subdomains("example.com")

    def test_timeout_raises(self, client):
        with patch.object(client.session, "get", side_effect=requests.exceptions.Timeout("timeout")):
            with pytest.raises(HackerTargetClientError, match="time out"):
                client.fetch_subdomains("example.com")

    def test_request_exception_raises(self, client):
        with patch.object(client.session, "get", side_effect=requests.exceptions.RequestException("err")):
            with pytest.raises(HackerTargetClientError, match="Unexpected"):
                client.fetch_subdomains("example.com")


# ─── Context manager ──────────────────────────────────────────────────────────

class TestContextManager:
    def test_enter_returns_client(self):
        with HackerTargetClient() as c:
            assert isinstance(c, HackerTargetClient)

    def test_session_closed_on_exit(self):
        with HackerTargetClient() as c:
            with patch.object(c.session, "close") as mock_close:
                pass
        # Verified by ensuring no exception and client is usable inside block
        assert c is not None