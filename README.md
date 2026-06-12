# SUBHUNT

> **Professional subdomain enumeration via Certificate Transparency logs, HackerTarget & RapidDNS — with HTTP liveness probing**

[![CI](https://github.com/ahmadouniass/Subdomains-finder-subhunt/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmadouniass/Subdomains-finder-subhunt/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`subhunt` is a modular, production-grade OSINT tool that harvests **subdomains** from multiple passive sources — [crt.sh](https://crt.sh) Certificate Transparency logs, [HackerTarget](https://hackertarget.com), and [RapidDNS](https://rapiddns.io) — merges results automatically, and can **probe each subdomain for HTTP/HTTPS liveness**.

Designed for **bug bounty hunters**, **penetration testers**, and **security researchers** who need fast, reliable, repeatable subdomain enumeration as part of their reconnaissance workflow.

---

## Features

| Feature | Details |
|---|---|
| **Multi-source enumeration** | crt.sh + HackerTarget + RapidDNS — merged & deduplicated automatically |
| **HTTP/HTTPS liveness probing** | Checks each subdomain with HTTPS-first, HTTP-fallback; returns status code & final URL |
| **`[200]` / `[DEAD]` badges** | Colour-coded status next to each result in the terminal |
| **Alive-only mode** | `--alive-only` filters output & exports to reachable hosts only |
| **crt.sh health check** | Detects when crt.sh is down and falls back to HackerTarget and RapidDNS |
| **Wildcard cleaning** | Strips `*.` and `%.` prefixes, deduplicates, lowercases, scope-validates |
| **Multi-format export** | TXT (one per line), JSON (structured + metadata), CSV (indexed, with probe columns) |
| **Retry & timeout** | Exponential back-off via `urllib3` on 429/5xx |
| **Pretty terminal output** | Colour-coded results with animated spinner (via `colorama`) |
| **Verbose / debug mode** | Full DEBUG log to console and rotating log file under `logs/` |
| **Modular architecture** | Each concern in its own module — fully unit-tested |
| **pip-installable CLI** | `pip install .` registers the `subhunt` command globally |
| **233 unit tests** | Zero real network calls — all HTTP mocked, coverage ≥ 80% enforced in CI |

---

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/ahmadouniass/Subdomains-finder-subhunt.git
cd Subdomains-finder-subhunt
python3 -m venv .venv #for the linux user or "python -m venv .venv" for the windows user
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Quick run without installation

```bash
pip install requests colorama beautifulsoup4
python main.py -d example.com
```

---

## Usage

### Basic scan (crt.sh + HackerTarget + RapidDNS)

```bash
subhunt -d example.com
```

### Probe subdomains for liveness after enumeration

```bash
subhunt -d example.com --probe
```

### Only show and export alive subdomains

```bash
subhunt -d example.com --probe --alive-only
```

### Probe with custom concurrency and timeout

```bash
subhunt -d example.com --probe --probe-workers 50 --probe-timeout 3
```

### Disable specific sources

```bash
subhunt -d example.com --disable-hackertarget --disable-rapiddns
```

### All export formats + verbose

```bash
subhunt -d example.com -f txt json csv -v
```

### Tuned network + custom output directory

```bash
subhunt -d example.com -f json csv -o /tmp/recon --timeout 60 --retries 5 --backoff 3.0
```

### Suppress banner (scripting / piping)

```bash
subhunt -d example.com --no-banner --no-file-log
```

---

## Full Options

```
usage: subhunt [-h] -d DOMAIN [-f FORMAT [FORMAT ...]] [-o DIR]
               [--no-export] [--disable-hackertarget] [--disable-rapiddns]
               [--probe] [--probe-timeout SEC] [--probe-workers N] [--alive-only]
               [--timeout SEC] [--retries N] [--backoff FACTOR]
               [-v] [--log-dir DIR] [--no-file-log]
               [--version] [--no-banner]

target:
  -d, --domain DOMAIN          Apex domain to enumerate (e.g. example.com)

output:
  -f, --formats FORMAT ...     Export format(s): txt json csv  (default: txt)
  -o, --output-dir DIR         Output directory               (default: ./output)
  --no-export                  Skip file export; print results only

sources:
  --disable-hackertarget       Disable HackerTarget API (enabled by default)
  --disable-rapiddns           Disable RapidDNS scraping (enabled by default)

probing:
  --probe                      After enumeration, check which subdomains are alive (HTTP/HTTPS)
  --probe-timeout SEC          Timeout per probe request in seconds (default: 5)
  --probe-workers N            Parallel threads for probing                (default: 20)
  --alive-only                 Only display/export alive subdomains (requires --probe)

network:
  --timeout SEC                HTTP request timeout in seconds (default: 30)
  --retries N                  Number of retry attempts        (default: 3)
  --backoff FACTOR             Exponential back-off factor     (default: 2.0)

logging:
  -v, --verbose                Enable DEBUG-level console output
  --log-dir DIR                Rotating log file directory     (default: ./logs)
  --no-file-log                Disable file logging entirely
```

---

## Output Example

### Without probing

```
  [*] Target domain    : example.com
  [*] Sources          : CRT.sh + HackerTarget + RapidDNS
  [*] Export formats   : txt, json, csv
  [*] Output directory : output
  [*] Timeout / Retries: 30s / 3

  ⠸  Enumerating subdomains for example.com …

  ────────────────────────────────────────────────────────────
    Results for example.com
  ────────────────────────────────────────────────────────────
    1.  api.example.com
    2.  dev.example.com
    3.  mail.example.com
    4.  vpn.example.com
    5.  www.example.com

  [*] Domain           : example.com
  [*] Cert records     : 312
  [*] HackerTarget     : 3
  [*] RapidDNS         : 2
  [*] Unique subdomains: 5
  [*] Elapsed time     : 2.41s

  [+] Done. 5 unique subdomain(s) found for example.com.
```

### With `--probe`

```
  [*] Target domain    : example.com
  [*] Probing          : enabled (20 workers, 5s timeout)

  ────────────────────────────────────────────────────────────
    Results for example.com
  ────────────────────────────────────────────────────────────
    1.  api.example.com          [200]
    2.  dev.example.com          [301]
    3.  mail.example.com         [DEAD]
    4.  vpn.example.com          [DEAD]
    5.  www.example.com          [200]

  [*] Unique subdomains: 5
  [*] Alive            : 3
  [*] Dead             : 2
  [*] Elapsed time     : 4.87s
```

---

## How It Works

1. **Health check** — `CRTClient.health_check()` pings crt.sh (5s timeout). If unreachable, the step is skipped automatically.
2. **crt.sh query** — `GET https://crt.sh/?q=%.{domain}&output=json` with retry-aware session.
3. **HackerTarget query** — `GET https://api.hackertarget.com/hostsearch/?q={domain}` (plain-text CSV).
4. **RapidDNS query** — `GET https://rapiddns.io/subdomain/{domain}?full=1`, HTML table parsed via BeautifulSoup4.
5. **Parse & clean** — wildcards stripped (`*.` and `%.`), scope-filtered, lowercased, RFC-1123 validated.
6. **Merge & deduplicate** — results from all sources merged into a `set`, then sorted alphabetically.
7. **Probe** *(optional, `--probe`)* — each subdomain is hit over HTTPS then HTTP; status code, final URL, and redirect chain are recorded. Concurrency controlled by `--probe-workers`.
8. **Filter** *(optional, `--alive-only`)* — dead subdomains are removed from the result set before export.
9. **Export** — timestamped files written under `output/`. CSV and JSON are enriched with probe data when probing was enabled.
10. **Display** — colour-coded terminal output with spinner, per-subdomain badges, and summary counters.

---

## Project Structure

```
subhunt/
├── main.py                        # CLI entry point (argparse)
├── subhunt/                       # Core package
│   ├── __init__.py
│   ├── cli.py                     # Installable CLI (pip entry point)
│   ├── client.py                  # crt.sh HTTP client (retry / health check)
│   ├── hackertarget_client.py     # HackerTarget API client
│   ├── rapiddns_client.py         # RapidDNS scraper (BeautifulSoup4)
│   ├── prober.py                  # Concurrent HTTP/HTTPS liveness prober
│   ├── parser.py                  # Extraction & cleaning
│   ├── validator.py               # Input validation
│   ├── exporter.py                # TXT / JSON / CSV writers (probe-aware)
│   ├── scanner.py                 # Multi-source orchestrator
│   ├── display.py                 # Terminal output (colours, badges, spinner)
│   ├── logger.py                  # Console + rotating file logger
│   └── exceptions.py             # Custom exception hierarchy
├── tests/
│   ├── conftest.py
│   ├── test_client.py             # 10 tests
│   ├── test_hackertarget.py       # 23 tests
│   ├── test_rapiddns.py           # 17 tests
│   ├── test_prober.py             # 23 tests
│   ├── test_parser.py             # 19 tests
│   ├── test_validator.py          # 17 tests
│   ├── test_exporter.py           # 14 tests
│   ├── test_scanner.py            # 34 tests
│   ├── test_display.py            # 33 tests
│   └── test_logger.py             # 13 tests
├── .github/workflows/
│   ├── ci.yml                     # CI: 3 OS × 3 Python versions
│   └── release.yml                # Release on version tag
├── requirements.txt
├── setup.py
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=subhunt --cov-report=term-missing --cov-fail-under=80
```

---

## JSON Output Schema

### Without probing

```json
{
  "meta": {
    "domain": "example.com",
    "total": 5,
    "generated_at": "2026-06-12T10:45:23+00:00",
    "tool": "subhunt",
    "cert_records_fetched": 312,
    "hackertarget_results": 3,
    "rapiddns_results": 2,
    "sources": ["crt.sh", "hackertarget", "rapiddns"],
    "crtsh_available": true
  },
  "subdomains": ["api.example.com", "dev.example.com", "mail.example.com"]
}
```

### With `--probe`

```json
{
  "meta": { "...": "same as above" },
  "subdomains": ["api.example.com", "dev.example.com", "mail.example.com"],
  "probe_results": [
    { "subdomain": "api.example.com",  "alive": true,  "status_code": 200, "url": "https://api.example.com/", "protocol": "https" },
    { "subdomain": "dev.example.com",  "alive": true,  "status_code": 301, "url": "https://dev.example.com/", "protocol": "https" },
    { "subdomain": "mail.example.com", "alive": false, "status_code": null, "url": null, "protocol": null }
  ]
}
```

---

## Limitations & Disclaimer

- **crt.sh instability**: crt.sh is a free service, often slow or unavailable (502/503). The tool automatically detects this and falls back to HackerTarget and RapidDNS. Use `--retries 5 --backoff 4.0` on slow connections.
- **HackerTarget rate limit**: Free tier limited to 50 requests/day.
- **Probing generates real HTTP traffic**: `--probe` sends actual requests to discovered hosts. Only use against targets you are authorized to test.
- **Self-signed certificates**: The prober disables SSL verification (`verify=False`) to avoid false negatives on subdomains with self-signed certs.
- **Legal**: Always obtain written authorization before performing reconnaissance on systems you do not own.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests for new functionality
4. Ensure `pytest tests/ -v --cov=subhunt --cov-fail-under=80` passes
5. Run `black --line-length=115 subhunt/ main.py` and `flake8 subhunt/ main.py --max-line-length=115`
6. Submit a pull request