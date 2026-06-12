# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.4.0] - 2026-06-12

### Added

- **HTTP/HTTPS probing** (`subhunt/prober.py`) — after enumeration, subhunt can now
  check which discovered subdomains are actually reachable. Each subdomain is probed
  over HTTPS first, then HTTP as a fallback. Results carry the final HTTP status code,
  final URL after redirects, and protocol used.
- **`--probe` flag** — opt-in CLI flag to enable liveness probing after enumeration.
- **`--probe-timeout SEC`** — per-request timeout for each probe attempt (default: 5 s).
- **`--probe-workers N`** — number of parallel probe threads via `ThreadPoolExecutor`
  (default: 20), keeping probing fast even for large subdomain sets.
- **`--alive-only` flag** — when combined with `--probe`, only alive subdomains are
  displayed and exported; dead ones are silently dropped.
- **`[200]` / `[DEAD]` badges in terminal output** — each subdomain line now shows a
  colour-coded status badge when probing is enabled: green HTTP status code for alive
  hosts, red `[DEAD]` for unreachable ones.
- **Alive / Dead counts in scan summary** — the summary block prints `Alive` and `Dead`
  counters when at least one subdomain was probed.
- **Enriched CSV export** — with `--probe`, the CSV gains three extra columns:
  `alive` (bool), `status_code` (int), `url` (final URL after redirects).
- **Enriched JSON export** — with `--probe`, the JSON payload includes a
  `probe_results` array with per-subdomain probing details.
- **`ScanResult.probe_results`** — list of `ProbeResult` objects, accessible
  programmatically when using subhunt as a library.
- **`ScanResult.alive_count` / `ScanResult.dead_count`** — computed properties
  derived from `probe_results`.
- **`ScanConfig.probe`, `probe_timeout`, `probe_workers`, `alive_only`** — new library
  API fields to control probing behaviour programmatically.

### Fixed
- `subhunt.cli:main` registered as the proper pip entry point (fixes
  `ModuleNotFoundError` when running `subhunt` after `pip install`).

---

## [1.3.0] - 2026-06-08

### Added
- **RapidDNS source** — scrapes `rapiddns.io/subdomain/{domain}?full=1` and merges
  results with crt.sh and HackerTarget automatically.
- **`--disable-rapiddns` flag** — opt-out of RapidDNS scraping.
- **17 new tests** in `test_rapiddns.py` covering parsing, error scenarios, rate limiting.

### Changed
- CLI summary: separate counts for HackerTarget and RapidDNS findings.
- `ScanConfig`: new `use_rapiddns: bool = True` field.
- `ScanResult`: new `rapiddns_count` field.
- JSON export metadata: added `rapiddns_results` counter.

---

## [1.2.0] - 2026-06-06

### Changed
- Project renamed `crtsh-recon` → `subhunt` across package, CLI command, `setup.py`, logger namespace, and documentation.

---

## [1.1.0] - 2026-06-05

### Added
- **HackerTarget integration** (`hackertarget_client.py`) — merges results from `api.hackertarget.com/hostsearch/`.
- **crt.sh health check** — `CRTClient.health_check()` auto-detects downtime and falls back to HackerTarget.
- **`--disable-hackertarget` flag**.
- 23 tests in `test_hackertarget.py`; `test_scanner.py` fully rewritten (27 tests).

### Changed
- `scanner.py` redesigned: health check → crt.sh → HackerTarget → merge → export.
- `ScanConfig`: new `use_hackertarget: bool = True` field.

---

## [1.0.0] - 2026-06-03

### Added
- Initial release — subdomain enumeration via crt.sh Certificate Transparency logs.
- Modular architecture: `client`, `parser`, `validator`, `exporter`, `scanner`, `display`, `logger`.
- CLI with argparse, TXT/JSON/CSV export, retry back-off, colorama spinner.
- 117 unit tests, CI matrix (3 OS × 3 Python versions), 80% coverage gate, MIT license.

---

## Unreleased

### Planned
- DNS resolution for discovered subdomains
- PyPI release (`pip install subhunt`)