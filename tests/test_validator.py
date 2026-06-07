"""
tests/test_validator.py — Unit tests for subhunt.validator
"""

import pytest
from subhunt.validator import validate_domain, validate_formats
from subhunt.exceptions import ValidationError


class TestValidateDomain:
    def test_simple_apex(self):
        assert validate_domain("example.com") == "example.com"

    def test_uppercase_normalised(self):
        assert validate_domain("EXAMPLE.COM") == "example.com"

    def test_leading_trailing_spaces(self):
        assert validate_domain("  example.com  ") == "example.com"

    def test_trailing_dot_stripped(self):
        assert validate_domain("example.com.") == "example.com"

    def test_http_scheme_stripped(self):
        assert validate_domain("http://example.com") == "example.com"

    def test_https_scheme_stripped(self):
        assert validate_domain("https://example.com") == "example.com"

    def test_url_with_path_stripped(self):
        assert validate_domain("https://example.com/some/path") == "example.com"

    def test_subdomain_accepted(self):
        # Users can pass a subdomain too — we just validate the syntax
        assert validate_domain("sub.example.com") == "sub.example.com"

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("   ")

    def test_single_label_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("localhost")

    def test_invalid_chars_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("exam_ple.com")

    def test_ip_address_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("192.168.1.1")


class TestValidateFormats:
    def test_valid_single_format(self):
        assert validate_formats(["txt"]) == ["txt"]

    def test_valid_multiple_formats(self):
        result = validate_formats(["txt", "json", "csv"])
        assert set(result) == {"txt", "json", "csv"}

    def test_uppercase_normalised(self):
        assert validate_formats(["TXT", "JSON"]) == ["txt", "json"]

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError, match="Unsupported"):
            validate_formats(["xml"])

    def test_mixed_valid_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate_formats(["txt", "pdf"])

    def test_empty_list_returns_empty(self):
        assert validate_formats([]) == []
