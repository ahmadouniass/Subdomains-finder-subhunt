"""
tests/test_exporter.py — Unit tests for crtsh_recon.exporter
"""

import csv
import json
import pytest

from crtsh_recon.exporter import export_txt, export_json, export_csv, export_results


DOMAIN = "example.com"
SUBDOMAINS = ["api.example.com", "mail.example.com", "www.example.com"]


@pytest.fixture
def out_dir(tmp_path) -> str:
    return str(tmp_path / "output")


# ---------------------------------------------------------------------------
# TXT
# ---------------------------------------------------------------------------

class TestExportTxt:
    def test_creates_file(self, out_dir):
        path = export_txt(SUBDOMAINS, DOMAIN, out_dir)
        assert path.exists()

    def test_content_one_per_line(self, out_dir):
        path = export_txt(SUBDOMAINS, DOMAIN, out_dir)
        lines = path.read_text().splitlines()
        assert lines == SUBDOMAINS

    def test_empty_subdomains(self, out_dir):
        path = export_txt([], DOMAIN, out_dir)
        assert path.read_text() == ""

    def test_custom_filename(self, out_dir):
        path = export_txt(SUBDOMAINS, DOMAIN, out_dir, filename="custom.txt")
        assert path.name == "custom.txt"


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

class TestExportJson:
    def test_creates_file(self, out_dir):
        path = export_json(SUBDOMAINS, DOMAIN, out_dir)
        assert path.exists()

    def test_valid_json(self, out_dir):
        path = export_json(SUBDOMAINS, DOMAIN, out_dir)
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_subdomains_in_payload(self, out_dir):
        path = export_json(SUBDOMAINS, DOMAIN, out_dir)
        data = json.loads(path.read_text())
        assert data["subdomains"] == SUBDOMAINS

    def test_meta_fields_present(self, out_dir):
        path = export_json(SUBDOMAINS, DOMAIN, out_dir)
        data = json.loads(path.read_text())
        assert data["meta"]["domain"] == DOMAIN
        assert data["meta"]["total"] == len(SUBDOMAINS)
        assert "generated_at" in data["meta"]

    def test_extra_metadata_embedded(self, out_dir):
        path = export_json(SUBDOMAINS, DOMAIN, out_dir, metadata={"custom": "value"})
        data = json.loads(path.read_text())
        assert data["meta"]["custom"] == "value"


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

class TestExportCsv:
    def test_creates_file(self, out_dir):
        path = export_csv(SUBDOMAINS, DOMAIN, out_dir)
        assert path.exists()

    def test_header_row(self, out_dir):
        path = export_csv(SUBDOMAINS, DOMAIN, out_dir)
        with path.open() as fh:
            reader = csv.reader(fh)
            header = next(reader)
        assert header == ["#", "subdomain"]

    def test_correct_row_count(self, out_dir):
        path = export_csv(SUBDOMAINS, DOMAIN, out_dir)
        with path.open() as fh:
            rows = list(csv.reader(fh))
        # header + data rows
        assert len(rows) == len(SUBDOMAINS) + 1

    def test_index_column(self, out_dir):
        path = export_csv(SUBDOMAINS, DOMAIN, out_dir)
        with path.open() as fh:
            reader = csv.reader(fh)
            next(reader)  # skip header
            first_data_row = next(reader)
        assert first_data_row[0] == "1"
        assert first_data_row[1] == SUBDOMAINS[0]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class TestExportResults:
    def test_all_formats_written(self, out_dir):
        written = export_results(SUBDOMAINS, DOMAIN, ["txt", "json", "csv"], out_dir)
        assert set(written.keys()) == {"txt", "json", "csv"}
        for path in written.values():
            assert path.exists()

    def test_only_requested_formats(self, out_dir):
        written = export_results(SUBDOMAINS, DOMAIN, ["json"], out_dir)
        assert "json" in written
        assert "txt" not in written

    def test_empty_formats_returns_empty(self, out_dir):
        written = export_results(SUBDOMAINS, DOMAIN, [], out_dir)
        assert written == {}

    def test_unknown_format_skipped(self, out_dir):
        # Should not raise; unknown formats are logged and skipped
        written = export_results(SUBDOMAINS, DOMAIN, ["txt", "xml"], out_dir)
        assert "txt" in written
        assert "xml" not in written
