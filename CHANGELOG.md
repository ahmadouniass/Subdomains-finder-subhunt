# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Multi-source subdomain enumeration: CRT.sh + HackerTarget API integration
- `--disable-hackertarget` flag to use CRT.sh exclusively
- `HackerTargetClient` for robust HackerTarget API querying with retry logic
- `HackerTargetClientError` exception type for HackerTarget-specific errors
- Enhanced scanner to merge results from multiple sources and deduplicate
- Comprehensive test suite for HackerTarget client (`test_hackertarget.py`)

### Changed
- `ScanResult` now includes `hackertarget_count` field to track results per source
- `ScanConfig` now includes `use_hackertarget` boolean flag (default: True)
- JSON export metadata now includes `hackertarget_results` and `sources` list

---

## [1.0.0] - 2024-06-03

### Added
- Initial public release of `crtsh-recon`
- Subdomain enumeration via [crt.sh](https://crt.sh) Certificate Transparency logs
- Modular architecture: `client`, `parser`, `validator`, `exporter`, `scanner`, `display`, `logger`
- CLI entry point via `argparse` (`--domain`, `--formats`, `--timeout`, `--retries`, `--backoff`, `--verbose`)
- Multi-format export: TXT, JSON (with metadata), CSV (indexed)
- Retry strategy with exponential back-off on HTTP 429/5xx errors
- Colour terminal output with animated spinner (via `colorama`)
- Rotating file logger under `logs/`
- `pip install .` support — registers `crtsh-recon` as a global CLI command
- 117 unit tests across 7 test modules (zero real network calls)
- CI matrix: Ubuntu / macOS / Windows × Python 3.10 / 3.11 / 3.12
- Coverage gate: 80% minimum enforced in CI

### Fixed
- `_strip_wildcard` now handles both `*.` (X.509) and `%.` (crt.sh SQL) prefixes
  via `startswith` instead of a regex that behaved inconsistently on Windows/Python 3.13
- `logger.py` now catches `(OSError, ValueError)` to handle null-byte paths on all OS
- CI workflow now uses OS-conditional steps to avoid PowerShell `\` line-continuation errors on Windows runners

---

## Planned

### Future Features
- PyPI release (`pip install crtsh-recon`)
- Additional DNS sources (RapidDNS, AlienVault OTX)
- DNS resolution of discovered subdomains
