"""
tests/test_rapiddns.py — Unit tests for subhunt.rapiddns_client
"""

import pytest
import requests
from unittest.mock import Mock, patch

from subhunt.rapiddns_client import RapidDNSClient, _parse_html
from subhunt.exceptions import RapidDNSClientError


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _mock_response(status_code: int, text: str = "") -> Mock:
    mock = Mock()
    mock.status_code = status_code
    mock.ok = 200 <= status_code < 300
    mock.text = text
    mock.content = text.encode()
    return mock


def _make_html(subdomains: list[str]) -> str:
    """Build a minimal HTML page mimicking RapidDNS table structure."""
    rows = "\n".join(
        f"<tr><td>{sub}</td><td>A</td><td>1.2.3.4</td></tr>"
        for sub in subdomains
    )
    return f"""
    <html><body>
    <table>
      <thead><tr><th>Subdomain</th><th>Type</th><th>IP</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </body></html>
    """


@pytest.fixture
def client():
    return RapidDNSClient(timeout=5, retries=1, backoff=0.0)


# ─── _parse_html (unit) ───────────────────────────────────────────────────────

class TestParseHtml:
    def test_extracts_subdomains_from_table(self):
        html = _make_html(["api.example.com", "mail.example.com"])
        result = _parse_html(html)
        assert "api.example.com" in result
        assert "mail.example.com" in result

    def test_empty_table_returns_empty(self):
        html = "<html><body><table></table></body></html>"
        result = _parse_html(html)
        assert result == []

    def test_no_table_returns_empty(self):
        html = "<html><body><p>No results</p></body></html>"
        result = _parse_html(html)
        assert result == []

    def test_lowercase_normalisation(self):
        html = _make_html(["API.EXAMPLE.COM", "Mail.Example.Com"])
        result = _parse_html(html)
        assert "api.example.com" in result
        assert "mail.example.com" in result

    def test_header_row_skipped(self):
        """thead row has no <td> — must be skipped."""
        html = _make_html(["www.example.com"])
        result = _parse_html(html)
        # "Subdomain" header text must not appear
        assert "subdomain" not in result

    def test_multiple_subdomains(self):
        subs = [f"sub{i}.example.com" for i in range(10)]
        html = _make_html(subs)
        result = _parse_html(html)
        assert len(result) == 10

    def test_invalid_html_does_not_crash(self):
        result = _parse_html("<<not valid html>>")
        assert isinstance(result, list)


# ─── fetch_subdomains — happy path ────────────────────────────────────────────

class TestFetchSubdomainsSuccess:
    def test_returns_set_of_subdomains(self, client):
        html = _make_html(["api.example.com", "mail.example.com"])
        with patch.object(client.session, "get", return_value=_mock_response(200, html)):
            result = client.fetch_subdomains("example.com")
        assert "api.example.com" in result
        assert "mail.example.com" in result

    def test_returns_set_type(self, client):
        html = _make_html(["www.example.com"])
        with patch.object(client.session, "get", return_value=_mock_response(200, html)):
            result = client.fetch_subdomains("example.com")
        assert isinstance(result, set)

    def test_deduplication(self, client):
        # Same subdomain twice in table
        html = _make_html(["api.example.com", "api.example.com"])
        with patch.object(client.session, "get", return_value=_mock_response(200, html)):
            result = client.fetch_subdomains("example.com")
        assert len(result) == 1

    def test_correct_url_called(self, client):
        html = _make_html(["www.example.com"])
        with patch.object(client.session, "get", return_value=_mock_response(200, html)) as mock_get:
            client.fetch_subdomains("example.com")
        call_url = mock_get.call_args[0][0]
        assert "rapiddns.io" in call_url
        assert "example.com" in call_url

    def test_full_param_sent(self, client):
        html = _make_html(["www.example.com"])
        with patch.object(client.session, "get", return_value=_mock_response(200, html)) as mock_get:
            client.fetch_subdomains("example.com")
        params = mock_get.call_args[1]["params"]
        assert params.get("full") == "1"


# ─── fetch_subdomains — empty / no results ────────────────────────────────────

class TestFetchSubdomainsEmpty:
    def test_no_result_marker_returns_empty(self, client):
        html = "<html><body><p>no result found</p></body></html>"
        with patch.object(client.session, "get", return_value=_mock_response(200, html)):
            result = client.fetch_subdomains("nxdomain.com")
        assert result == set()

    def test_no_table_returns_empty(self, client):
        html = "<html><body><p>nothing here</p></body></html>"
        with patch.object(client.session, "get", return_value=_mock_response(200, html)):
            result = client.fetch_subdomains("example.com")
        assert result == set()

    def test_empty_html_returns_empty(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(200, "")):
            result = client.fetch_subdomains("example.com")
        assert result == set()


# ─── fetch_subdomains — error handling ────────────────────────────────────────

class TestFetchSubdomainsErrors:
    def test_rate_limit_429_raises(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(429, "")):
            with pytest.raises(RapidDNSClientError, match="Rate limited"):
                client.fetch_subdomains("example.com")

    def test_http_500_raises(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(500, "")):
            with pytest.raises(RapidDNSClientError, match="HTTP 500"):
                client.fetch_subdomains("example.com")

    def test_http_503_raises(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(503, "")):
            with pytest.raises(RapidDNSClientError, match="HTTP 503"):
                client.fetch_subdomains("example.com")

    def test_connection_error_raises(self, client):
        with patch.object(
            client.session, "get",
            side_effect=requests.exceptions.ConnectionError("fail")
        ):
            with pytest.raises(RapidDNSClientError, match="Connection failed"):
                client.fetch_subdomains("example.com")

    def test_timeout_raises(self, client):
        with patch.object(
            client.session, "get",
            side_effect=requests.exceptions.Timeout("timeout")
        ):
            with pytest.raises(RapidDNSClientError, match="timed out"):
                client.fetch_subdomains("example.com")

    def test_request_exception_raises(self, client):
        with patch.object(
            client.session, "get",
            side_effect=requests.exceptions.RequestException("err")
        ):
            with pytest.raises(RapidDNSClientError, match="Unexpected"):
                client.fetch_subdomains("example.com")


# ─── Context manager ──────────────────────────────────────────────────────────

class TestContextManager:
    def test_enter_returns_client(self):
        with RapidDNSClient() as c:
            assert isinstance(c, RapidDNSClient)

    def test_usable_inside_context(self):
        with RapidDNSClient() as c:
            assert hasattr(c, "fetch_subdomains")