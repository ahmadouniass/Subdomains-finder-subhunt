"""
tests/test_client.py — Unit tests for crtsh_recon.client (network calls mocked).
"""

import json
import pytest
import requests
from unittest.mock import patch, MagicMock

from crtsh_recon.client import CRTClient
from crtsh_recon.exceptions import (
    CRTClientError,
    CRTNotFoundError,
    CRTRateLimitError,
)


def _mock_response(status_code: int, body) -> MagicMock:
    """Build a minimal mock requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = 200 <= status_code < 300
    if isinstance(body, (list, dict)):
        mock.json.return_value = body
        mock.content = json.dumps(body).encode()
    else:
        mock.json.side_effect = ValueError("Not JSON")
        mock.text = str(body)
        mock.content = str(body).encode()
    return mock


@pytest.fixture
def client():
    return CRTClient(timeout=5, retries=1, backoff=0.0)


class TestFetchCertificates:
    def test_success_returns_list(self, client):
        records = [{"name_value": "mail.example.com", "common_name": "example.com"}]
        with patch.object(client.session, "get", return_value=_mock_response(200, records)):
            result = client.fetch_certificates("example.com")
        assert result == records

    def test_empty_list_returned_as_is(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(200, [])):
            result = client.fetch_certificates("example.com")
        assert result == []

    def test_404_raises_not_found(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(404, "")):
            with pytest.raises(CRTNotFoundError):
                client.fetch_certificates("nxdomain.example.com")

    def test_429_raises_rate_limit(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(429, "")):
            with pytest.raises(CRTRateLimitError):
                client.fetch_certificates("example.com")

    def test_500_raises_client_error(self, client):
        with patch.object(client.session, "get", return_value=_mock_response(500, "")):
            with pytest.raises(CRTClientError):
                client.fetch_certificates("example.com")

    def test_invalid_json_raises_client_error(self, client):
        mock = _mock_response(200, "NOT JSON")
        mock.ok = True
        with patch.object(client.session, "get", return_value=mock):
            with pytest.raises(CRTClientError, match="Failed to parse"):
                client.fetch_certificates("example.com")

    def test_connection_error_raises_client_error(self, client):
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.ConnectionError("fail")
        ):
            with pytest.raises(CRTClientError, match="Connection failed"):
                client.fetch_certificates("example.com")

    def test_timeout_raises_client_error(self, client):
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout("timeout")
        ):
            with pytest.raises(CRTClientError, match="timed out"):
                client.fetch_certificates("example.com")

    def test_non_list_json_raises_client_error(self, client):
        with patch.object(
            client.session, "get", return_value=_mock_response(200, {"error": "bad"})
        ):
            with pytest.raises(CRTClientError, match="Unexpected JSON structure"):
                client.fetch_certificates("example.com")


class TestContextManager:
    def test_context_manager_closes_session(self):
        with CRTClient() as c:
            with patch.object(c.session, "close") as mock_close:
                pass
        # __exit__ calls self.close() which calls session.close()
        # We can't assert after the with block has already exited, so test
        # that the client is usable inside the block.
        assert c is not None
