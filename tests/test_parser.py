"""
tests/test_parser.py — Unit tests for crtsh_recon.parser
"""

from crtsh_recon.parser import (
    extract_subdomains,
    _strip_wildcard,
    _is_valid_subdomain,
    _split_name_value,
)


# ---------------------------------------------------------------------------
# _strip_wildcard
# ---------------------------------------------------------------------------


class TestStripWildcard:
    def test_strips_wildcard_prefix(self):
        assert _strip_wildcard("*.example.com") == "example.com"

    def test_strips_percent_prefix(self):          # ← nouveau
        assert _strip_wildcard("%.example.com") == "example.com"

    def test_no_wildcard_unchanged(self):
        assert _strip_wildcard("sub.example.com") == "sub.example.com"

    def test_multiple_wildcards_only_leading_stripped(self):
        assert _strip_wildcard("*.*.example.com") == "*.example.com"

    def test_multiple_percent_only_leading_stripped(self):  # ← nouveau
        assert _strip_wildcard("%.%.example.com") == "%.example.com"

# ---------------------------------------------------------------------------
# _is_valid_subdomain
# ---------------------------------------------------------------------------


class TestIsValidSubdomain:
    def test_valid_subdomain(self):
        assert _is_valid_subdomain("mail.example.com", "example.com") is True

    def test_apex_itself_is_valid(self):
        assert _is_valid_subdomain("example.com", "example.com") is True

    def test_different_domain_rejected(self):
        assert _is_valid_subdomain("evil.com", "example.com") is False

    def test_empty_string_rejected(self):
        assert _is_valid_subdomain("", "example.com") is False

    def test_wildcard_rejected(self):
        assert _is_valid_subdomain("*.example.com", "example.com") is False

    def test_underscore_invalid(self):
        assert _is_valid_subdomain("_dmarc.example.com", "example.com") is False

    def test_deep_subdomain(self):
        assert _is_valid_subdomain("a.b.c.example.com", "example.com") is True

    def test_similar_but_different_domain(self):
        # notexample.com should not match example.com
        assert _is_valid_subdomain("notexample.com", "example.com") is False


# ---------------------------------------------------------------------------
# _split_name_value
# ---------------------------------------------------------------------------


class TestSplitNameValue:
    def test_newline_separated(self):
        result = list(_split_name_value("a.example.com\nb.example.com"))
        assert result == ["a.example.com", "b.example.com"]

    def test_space_separated(self):
        result = list(_split_name_value("a.example.com b.example.com"))
        assert "a.example.com" in result
        assert "b.example.com" in result

    def test_single_value(self):
        result = list(_split_name_value("a.example.com"))
        assert result == ["a.example.com"]

    def test_empty_string(self):
        result = [x for x in _split_name_value("") if x]
        assert result == []


# ---------------------------------------------------------------------------
# extract_subdomains
# ---------------------------------------------------------------------------


class TestExtractSubdomains:
    def _make_record(self, name_value: str, common_name: str = "") -> dict:
        return {"name_value": name_value, "common_name": common_name}

    def test_basic_extraction(self):
        records = [self._make_record("mail.example.com")]
        result = extract_subdomains(records, "example.com")
        assert "mail.example.com" in result

    def test_deduplication(self):
        records = [
            self._make_record("mail.example.com"),
            self._make_record("mail.example.com"),
        ]
        result = extract_subdomains(records, "example.com")
        assert result.count("mail.example.com") == 1

    def test_out_of_scope_filtered(self):
        records = [self._make_record("evil.com")]
        result = extract_subdomains(records, "example.com")
        assert "evil.com" not in result

    def test_case_normalised(self):
        records = [self._make_record("MAIL.EXAMPLE.COM")]
        result = extract_subdomains(records, "example.com")
        assert "mail.example.com" in result

    def test_multi_name_value(self):
        records = [self._make_record("mail.example.com\napi.example.com")]
        result = extract_subdomains(records, "example.com")
        assert "mail.example.com" in result
        assert "api.example.com" in result

    def test_empty_records(self):
        result = extract_subdomains([], "example.com")
        assert result == []

    def test_sorted_output(self):
        records = [
            self._make_record("z.example.com"),
            self._make_record("a.example.com"),
            self._make_record("m.example.com"),
        ]
        result = extract_subdomains(records, "example.com")
        assert result == sorted(result)

    def test_common_name_also_extracted(self):
        records = [{"name_value": "", "common_name": "vpn.example.com"}]
        result = extract_subdomains(records, "example.com")
        assert "vpn.example.com" in result
        
    def test_wildcard_stripped(self):
        records = [self._make_record("*.example.com")]
        result = extract_subdomains(records, "example.com")
        assert "example.com" in result

    def test_percent_wildcard_stripped(self):      # ← nouveau
        records = [self._make_record("%.example.com")]
        result = extract_subdomains(records, "example.com")
        assert "example.com" in result