# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2024-06-05

### Added
- **HackerTarget integration** — new `hackertarget_client.py` module queries `https://api.hackertarget.com/hostsearch/` and merges results with crt.sh
- **crt.sh health check** — `CRTClient.health_check()` pings crt.sh before scanning; if unreachable, HackerTarget is used as automatic fallback
- **`--disable-hackertarget` CLI flag** — opt out of HackerTarget for crt.sh-only scans
- **`HackerTargetClientError`** added to the exception hierarchy in `exceptions.py`
- **`_parse_response()`** extracted as a public function in `hackertarget_client.py` for unit testability
- **`hackertarget_count`** and **`crtsh_available`** fields added to `ScanResult`
- **`test_hackertarget.py`** — 23 unit tests for the new client (mocked HTTP)
- **`test_scanner.py`** fully rewritten — 27 tests covering multi-source merge, fallback logic, health check, error isolation

### Changed
- `scanner.py` redesigned to orchestrate multiple sources: health check → crt.sh → HackerTarget → merge → export
- `ScanConfig` gains `use_hackertarget: bool = True`
- JSON export metadata now includes `hackertarget_results`, `sources`, and `crtsh_available`
- `_strip_wildcard()` in `parser.py` now handles both `*.` (X.509) and `%.` (crt.sh SQL) prefixes via `startswith` instead of regex
- README updated with new architecture, multi-source usage examples, and updated project structure

### Fixed
- `logger.py` now catches `(OSError, ValueError)` to handle null-byte paths on all OS
- CI workflow uses OS-conditional steps to avoid PowerShell `\` line-continuation errors on Windows runners
- f-string without placeholder in `main.py` (flake8 F541)

---

## [1.0.0] - 2026-06-03

### Added
- Initial public release of `crtsh-recon`
- Subdomain enumeration via [crt.sh](https://crt.sh) Certificate Transparency logs
- Modular architecture: `client`, `parser`, `validator`, `exporter`, `scanner`, `display`, `logger`
- CLI entry point via `argparse` with flags: `--domain`, `--formats`, `--timeout`, `--retries`, `--backoff`, `--verbose`
- Multi-format export: TXT, JSON (with metadata), CSV (indexed)
- Retry strategy with exponential back-off on HTTP 429/5xx errors
- Colour terminal output with animated spinner (via `colorama`)
- Rotating file logger under `logs/`
- `pip install .` support — registers `crtsh-recon` as a global CLI command
- 117 unit tests across 7 test modules (zero real network calls)
- CI matrix: Ubuntu / macOS / Windows × Python 3.10 / 3.11 / 3.12
- Coverage gate: 80% minimum enforced in CI
- GitHub Release workflow triggered on version tags
- `CHANGELOG.md` and `LICENSE` (MIT)

---

## Unreleased

### Planned
- DNS resolution of discovered subdomains
- AlienVault OTX as third enumeration source
- PyPI release (`pip install crtsh-recon`)