"""
tests/test_display.py — Unit tests for crtsh_recon.display
"""

import re
import sys
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from subhunt.display import (
    green, cyan, yellow, red, bold, dim,
    print_banner,
    print_section,
    print_info,
    print_success,
    print_warning,
    print_error,
    print_results,
    print_summary,
    Spinner,
)


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes so assertions work regardless of colorama."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ─── Colour helpers ───────────────────────────────────────────────────────────

class TestColourHelpers:
    def test_green_contains_text(self):
        assert "hello" in _strip_ansi(green("hello"))

    def test_cyan_contains_text(self):
        assert "hello" in _strip_ansi(cyan("hello"))

    def test_yellow_contains_text(self):
        assert "hello" in _strip_ansi(yellow("hello"))

    def test_red_contains_text(self):
        assert "hello" in _strip_ansi(red("hello"))

    def test_bold_contains_text(self):
        assert "hello" in _strip_ansi(bold("hello"))

    def test_dim_contains_text(self):
        assert "hello" in _strip_ansi(dim("hello"))

    def test_functions_return_strings(self):
        for fn in (green, cyan, yellow, red, bold, dim):
            assert isinstance(fn("x"), str)


# ─── Print helpers ────────────────────────────────────────────────────────────

class TestPrintHelpers:
    def _capture_stdout(self, fn, *args, **kwargs) -> str:
        buf = StringIO()
        with patch("sys.stdout", buf):
            fn(*args, **kwargs)
        return _strip_ansi(buf.getvalue())

    def _capture_stderr(self, fn, *args, **kwargs) -> str:
        buf = StringIO()
        with patch("sys.stderr", buf):
            fn(*args, **kwargs)
        return _strip_ansi(buf.getvalue())

    def test_print_banner_outputs_something(self):
        out = self._capture_stdout(print_banner)
        assert len(out) > 0

    def test_print_banner_contains_version(self):
        out = self._capture_stdout(print_banner, "2.0.0")
        assert "2.0.0" in out

    def test_print_section_contains_title(self):
        out = self._capture_stdout(print_section, "My Section")
        assert "My Section" in out

    def test_print_info_contains_message(self):
        out = self._capture_stdout(print_info, "hello info")
        assert "hello info" in out

    def test_print_success_contains_message(self):
        out = self._capture_stdout(print_success, "all good")
        assert "all good" in out

    def test_print_warning_goes_to_stderr(self):
        err = self._capture_stderr(print_warning, "watch out")
        assert "watch out" in err

    def test_print_error_goes_to_stderr(self):
        err = self._capture_stderr(print_error, "something broke")
        assert "something broke" in err


# ─── print_results ────────────────────────────────────────────────────────────

class TestPrintResults:
    def _capture(self, subdomains, domain="example.com") -> str:
        buf = StringIO()
        with patch("sys.stdout", buf):
            with patch("sys.stderr", StringIO()):
                print_results(subdomains, domain)
        return _strip_ansi(buf.getvalue())

    def test_empty_subdomains_prints_warning(self):
        err = StringIO()
        with patch("sys.stdout", StringIO()):
            with patch("sys.stderr", err):
                print_results([], "example.com")
        assert "No subdomains" in _strip_ansi(err.getvalue())

    def test_subdomains_appear_in_output(self):
        out = self._capture(["api.example.com", "www.example.com"])
        assert "api.example.com" in out
        assert "www.example.com" in out

    def test_domain_in_section_header(self):
        out = self._capture(["api.example.com"])
        assert "example.com" in out

    def test_index_numbers_present(self):
        out = self._capture(["a.example.com", "b.example.com", "c.example.com"])
        assert "1" in out
        assert "2" in out
        assert "3" in out

    def test_apex_only_result(self):
        out = self._capture(["example.com"])
        assert "example.com" in out

    def test_single_subdomain(self):
        out = self._capture(["only.example.com"])
        assert "only.example.com" in out


# ─── print_summary ────────────────────────────────────────────────────────────

class TestPrintSummary:
    def _capture(self, **kwargs) -> str:
        defaults = dict(
            domain="example.com",
            total=5,
            cert_count=42,
            exported={},
            elapsed=1.23,
        )
        defaults.update(kwargs)
        buf = StringIO()
        with patch("sys.stdout", buf):
            print_summary(**defaults)
        return _strip_ansi(buf.getvalue())

    def test_domain_in_summary(self):
        assert "example.com" in self._capture()

    def test_total_in_summary(self):
        assert "5" in self._capture()

    def test_cert_count_in_summary(self):
        assert "42" in self._capture()

    def test_elapsed_in_summary(self):
        assert "1.23" in self._capture()

    def test_exported_files_shown(self):
        from pathlib import Path
        out = self._capture(exported={"txt": Path("/tmp/out.txt")})
        assert "out.txt" in out

    def test_no_exported_files_no_crash(self):
        out = self._capture(exported={})
        assert "example.com" in out

    def test_hackertarget_count_in_summary(self):
        out = self._capture(hackertarget_count=10)
        assert "10" in out
        assert "HackerTarget" in out

    def test_rapiddns_count_in_summary(self):
        out = self._capture(rapiddns_count=15)
        assert "15" in out
        assert "RapidDNS" in out

    def test_sources_not_shown_when_zero(self):
        out = self._capture(hackertarget_count=0, rapiddns_count=0)
        assert "HackerTarget" not in out
        assert "RapidDNS" not in out


# ─── Spinner ──────────────────────────────────────────────────────────────────

class TestSpinner:
    """Force _is_tty=False on the instance to stay CI-safe (no thread)."""

    def _make_spinner(self, message="Testing") -> Spinner:
        s = Spinner(message)
        s._is_tty = False  # override instance attribute directly
        return s

    def test_context_manager_no_tty(self):
        buf = StringIO()
        with patch("sys.stdout", buf):
            with self._make_spinner():
                pass

    def test_message_printed_in_non_tty(self):
        buf = StringIO()
        with patch("sys.stdout", buf):
            with self._make_spinner("Working hard"):
                pass
        assert "Working hard" in _strip_ansi(buf.getvalue())

    def test_no_exception_on_exit(self):
        with self._make_spinner("No crash"):
            pass

    def test_spinner_with_exception_in_block(self):
        """Spinner __exit__ must not suppress exceptions."""
        with pytest.raises(ValueError):
            with self._make_spinner("Will fail"):
                raise ValueError("intentional")

    def test_spinner_enter_returns_self(self):
        s = self._make_spinner()
        result = s.__enter__()
        s.__exit__(None, None, None)
        assert result is s


# ─── print_results with probe data ───────────────────────────────────────────


class TestPrintResultsWithProbe:
    """Tests for the probe badge display in print_results."""

    def _capture(self, subdomains, domain="example.com", probe_results=None) -> str:
        buf = StringIO()
        with patch("sys.stdout", buf):
            with patch("sys.stderr", StringIO()):
                print_results(subdomains, domain, probe_results=probe_results)
        return _strip_ansi(buf.getvalue())

    def test_alive_badge_shown(self):
        from subhunt.prober import ProbeResult
        probes = [ProbeResult(subdomain="api.example.com", alive=True, status_code=200)]
        out = self._capture(["api.example.com"], probe_results=probes)
        assert "200" in out

    def test_dead_badge_shown(self):
        from subhunt.prober import ProbeResult
        probes = [ProbeResult(subdomain="api.example.com", alive=False)]
        out = self._capture(["api.example.com"], probe_results=probes)
        assert "DEAD" in out

    def test_mixed_alive_dead(self):
        from subhunt.prober import ProbeResult
        probes = [
            ProbeResult(subdomain="api.example.com", alive=True, status_code=200),
            ProbeResult(subdomain="dead.example.com", alive=False),
        ]
        out = self._capture(["api.example.com", "dead.example.com"], probe_results=probes)
        assert "200" in out
        assert "DEAD" in out

    def test_no_probe_results_no_badges(self):
        out = self._capture(["api.example.com"], probe_results=None)
        assert "DEAD" not in out
        assert "200" not in out

    def test_empty_probe_list_no_badges(self):
        out = self._capture(["api.example.com"], probe_results=[])
        assert "DEAD" not in out

    def test_unknown_subdomain_shows_question_mark(self):
        from subhunt.prober import ProbeResult
        # Probe data exists but not for this subdomain
        probes = [ProbeResult(subdomain="other.example.com", alive=True, status_code=200)]
        out = self._capture(["api.example.com"], probe_results=probes)
        assert "?" in out

    def test_alive_no_status_code_shows_ok(self):
        from subhunt.prober import ProbeResult
        probes = [ProbeResult(subdomain="api.example.com", alive=True, status_code=None)]
        out = self._capture(["api.example.com"], probe_results=probes)
        assert "OK" in out

    def test_status_403_shown(self):
        from subhunt.prober import ProbeResult
        probes = [ProbeResult(subdomain="api.example.com", alive=True, status_code=403)]
        out = self._capture(["api.example.com"], probe_results=probes)
        assert "403" in out


# ─── print_summary with alive/dead counts ────────────────────────────────────


class TestPrintSummaryProbe:
    def _capture(self, **kwargs) -> str:
        defaults = dict(
            domain="example.com",
            total=5,
            cert_count=42,
            exported={},
            elapsed=1.23,
        )
        defaults.update(kwargs)
        buf = StringIO()
        with patch("sys.stdout", buf):
            print_summary(**defaults)
        return _strip_ansi(buf.getvalue())

    def test_alive_count_shown_when_nonzero(self):
        out = self._capture(alive_count=10, dead_count=5)
        assert "Alive" in out
        assert "10" in out

    def test_dead_count_shown_when_nonzero(self):
        out = self._capture(alive_count=10, dead_count=5)
        assert "Dead" in out
        assert "5" in out

    def test_alive_dead_hidden_when_zero(self):
        out = self._capture(alive_count=0, dead_count=0)
        assert "Alive" not in out
        assert "Dead" not in out

    def test_alive_shown_dead_zero(self):
        out = self._capture(alive_count=3, dead_count=0)
        assert "Alive" in out
        assert "Dead" in out

