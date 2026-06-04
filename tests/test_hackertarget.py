"""
tests/test_hackertarget.py — Unit tests for crtsh_recon.hackertarget_client
"""

from unittest.mock import Mock, patch
import pytest

from crtsh_recon.hackertarget_client import HackerTargetClient
from crtsh_recon.exceptions import HackerTargetClientError


class TestHackerTargetClient:
    """Test suite for HackerTargetClient."""

    def test_fetch_subdomains_success(self):
        """Test successful subdomain fetch from HackerTarget."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "api.example.com,1.2.3.4\nmail.example.com,5.6.7.8\nexample.com,9.10.11.12\n"
        mock_response.content = mock_response.text.encode()

        with patch("crtsh_recon.hackertarget_client.requests.Session.get", return_value=mock_response):
            client = HackerTargetClient(timeout=30)
            result = client.fetch_subdomains("example.com")

            assert "api.example.com" in result
            assert "mail.example.com" in result
            assert "example.com" in result
            assert len(result) == 3

    def test_fetch_subdomains_no_results(self):
        """Test when HackerTarget returns error (no results)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "error"
        mock_response.content = b"error"

        with patch("crtsh_recon.hackertarget_client.requests.Session.get", return_value=mock_response):
            client = HackerTargetClient(timeout=30)
            result = client.fetch_subdomains("nonexistent.com")

            assert result == set()

    def test_fetch_subdomains_empty_response(self):
        """Test when HackerTarget returns empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.content = b""

        with patch("crtsh_recon.hackertarget_client.requests.Session.get", return_value=mock_response):
            client = HackerTargetClient(timeout=30)
            result = client.fetch_subdomains("example.com")

            assert result == set()

    def test_fetch_subdomains_rate_limit(self):
        """Test when HackerTarget rate limits (429)."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.content = b""

        with patch("crtsh_recon.hackertarget_client.requests.Session.get", return_value=mock_response):
            client = HackerTargetClient(timeout=30)

            with pytest.raises(HackerTargetClientError, match="rate limit"):
                client.fetch_subdomains("example.com")

    def test_fetch_subdomains_http_error(self):
        """Test when HackerTarget returns HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.ok = False
        mock_response.content = b""

        with patch("crtsh_recon.hackertarget_client.requests.Session.get", return_value=mock_response):
            client = HackerTargetClient(timeout=30)

            with pytest.raises(HackerTargetClientError, match="HTTP 500"):
                client.fetch_subdomains("example.com")

    def test_context_manager(self):
        """Test HackerTargetClient as context manager."""
        with HackerTargetClient(timeout=30) as client:
            assert client is not None
            assert hasattr(client, "fetch_subdomains")

    def test_lowercase_normalization(self):
        """Test that subdomains are normalized to lowercase."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "API.EXAMPLE.COM,1.2.3.4\nMail.Example.Com,5.6.7.8\n"
        mock_response.content = mock_response.text.encode()

        with patch("crtsh_recon.hackertarget_client.requests.Session.get", return_value=mock_response):
            client = HackerTargetClient(timeout=30)
            result = client.fetch_subdomains("example.com")

            assert "api.example.com" in result
            assert "mail.example.com" in result
            assert "API.EXAMPLE.COM" not in result
