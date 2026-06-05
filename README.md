# crtsh-recon

> **Professional subdomain enumeration via Certificate Transparency logs & HackerTarget**

[![CI](https://github.com/ahmadouniass/Subdomains-finder-crtsh/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmadouniass/Subdomains-finder-crtsh/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`crtsh-recon` is a modular, production-grade OSINT tool that harvests **subdomains** from multiple sources — [crt.sh](https://crt.sh) Certificate Transparency logs and [HackerTarget](https://hackertarget.com) — and merges the results automatically.

Designed for **bug bounty hunters**, **penetration testers**, and **security researchers** who need fast, reliable, repeatable subdomain enumeration as part of their reconnaissance workflow.

---

## Features

| Feature | Details |
|---|---|
| **Multi-source enumeration** | Queries crt.sh + HackerTarget in the same run, merges & deduplicates results |
| **crt.sh health check** | Detects when crt.sh is down and falls back to HackerTarget automatically |
| **Certificate Transparency** | `https://crt.sh/?q=%.domain&output=json` |
| **Wildcard & duplicate cleaning** | Strips `*.` and `%.` prefixes, deduplicates, lowercases, validates scope |
| **Multi-format export** | TXT (one per line), JSON (structured + metadata), CSV (indexed) |
| **Retry & timeout handling** | Exponential back-off via `urllib3.util.retry.Retry` on 429/5xx |
| **Pretty terminal output** | Colour-coded results with animated spinner (via `colorama`) |
| **Verbose / debug mode** | Full DEBUG log to console and rotating log file under `logs/` |
| **Modular architecture** | Each concern in its own module — fully unit-tested |
| **pip-installable CLI** | `pip install .` registers the `crtsh-recon` command globally |
| **167 unit tests** | Zero real network calls — all HTTP mocked, coverage ≥ 80 % enforced in CI |

---

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/ahmadouniass/Subdomains-finder-crtsh.git
cd Subdomains-finder-crtsh
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .                   # registers the crtsh-recon CLI command
```

### Quick run without installation

```bash
pip install requests colorama
python main.py -d example.com
```

---

## Usage

### Basic scan (crt.sh + HackerTarget)

```bash
crtsh-recon -d example.com
```

### crt.sh only

```bash
crtsh-recon -d example.com --disable-hackertarget
```

### All export formats + verbose

```bash
crtsh-recon -d example.com -f txt json csv -v
```

### Custom output directory + tuned network

```bash
crtsh-recon -d example.com -f json csv -o /tmp/recon --timeout 60 --retries 5 --backoff 3.0
```

### Suppress banner (scripting / piping)

```bash
crtsh-recon -d example.com --no-banner --no-file-log
```

### Full options

```
usage: crtsh-recon [-h] -d DOMAIN [-f FORMAT [FORMAT ...]] [-o DIR]
                   [--no-export] [--disable-hackertarget]
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
  --disable-hackertarget       Use CRT.sh only (HackerTarget enabled by default)

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

```
  [*] Target domain    : example.com
  [*] Sources          : CRT.sh + HackerTarget
  [*] Export formats   : txt, json, csv
  [*] Output directory : output
  [*] Timeout / Retries: 30s / 3

  ⠸  Querying sources for example.com …

  ────────────────────────────────────────────────────────────
    Results for example.com
  ────────────────────────────────────────────────────────────
    1.  api.example.com
    2.  dev.example.com
    3.  example.com
    4.  mail.example.com
    5.  staging.example.com
    6.  vpn.example.com
    7.  www.example.com

  ────────────────────────────────────────────────────────────
    Summary
  ────────────────────────────────────────────────────────────
  [*] Domain           : example.com
  [*] Cert records     : 312
  [*] Unique subdomains: 7
  [*] Elapsed time     : 2.41s

  [*] Exported files:
       TXT:  output/example.com_20240603_104523.txt
       JSON: output/example.com_20240603_104523.json
       CSV:  output/example.com_20240603_104523.csv

  [+] Done. 7 unique subdomain(s) found for example.com.
```

---

## Project Structure

```
crtsh-recon/
│
├── main.py                        # CLI entry point (argparse)
│
├── crtsh_recon/                   # Core package
│   ├── __init__.py                # Public API + version
│   ├── client.py                  # CRT.sh HTTP client (retry / timeout / health check)
│   ├── hackertarget_client.py     # HackerTarget API client
│   ├── parser.py                  # Subdomain extraction & cleaning
│   ├── validator.py               # Input validation (domain, formats)
│   ├── exporter.py                # TXT / JSON / CSV writers
│   ├── scanner.py                 # Orchestrator (multi-source merge)
│   ├── display.py                 # Terminal output (colours, spinner, tables)
│   ├── logger.py                  # Logging configuration (console + rotating file)
│   └── exceptions.py              # Custom exception hierarchy
│
├── tests/
│   ├── conftest.py                # Shared fixtures
│   ├── test_client.py             # CRT.sh client (mocked HTTP)
│   ├── test_hackertarget.py       # HackerTarget client (mocked HTTP)
│   ├── test_parser.py             # Parser unit tests
│   ├── test_validator.py          # Validator unit tests
│   ├── test_exporter.py           # Exporter unit tests
│   ├── test_scanner.py            # Orchestrator unit tests
│   ├── test_display.py            # Terminal output tests
│   └── test_logger.py             # Logging configuration tests
│
├── .github/workflows/
│   ├── ci.yml                     # CI: test matrix (3 OS × 3 Python versions)
│   └── release.yml                # Release: build + publish on version tag
│
├── output/                        # Default results directory (git-ignored)
├── logs/                          # Rotating log files (git-ignored)
│
├── requirements.txt
├── setup.py                       # pip install / CLI registration
├── CHANGELOG.md
├── LICENSE
├── .gitignore
└── README.md
```

---

## How It Works

1. **Health check** — `CRTClient.health_check()` pings crt.sh with a 5s timeout. If unreachable, the crt.sh step is skipped automatically.
2. **crt.sh query** — `GET https://crt.sh/?q=%.{domain}&output=json` with retry-aware session.
3. **HackerTarget query** — `GET https://api.hackertarget.com/hostsearch/?q={domain}` (plain-text CSV response).
4. **Parse & clean** — wildcards stripped (`*.` and `%.`), scope-filtered, lowercased, validated against RFC-1123.
5. **Merge & deduplicate** — results from both sources merged into a `set`, then sorted.
6. **Export** — timestamped files written under `output/` in the requested formats.
7. **Display** — colour-coded terminal output with spinner and summary block.

---

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# With coverage report (≥ 80% enforced)
pytest tests/ -v --cov=crtsh_recon --cov-report=term-missing --cov-fail-under=80
```

---

## JSON Output Schema

```json
{
  "meta": {
    "domain": "example.com",
    "total": 7,
    "generated_at": "2024-06-03T10:45:23+00:00",
    "tool": "crtsh-recon",
    "cert_records_fetched": 312,
    "hackertarget_results": 4,
    "sources": ["crt.sh", "hackertarget"],
    "crtsh_available": true
  },
  "subdomains": [
    "api.example.com",
    "dev.example.com",
    "example.com",
    "mail.example.com",
    "staging.example.com",
    "vpn.example.com",
    "www.example.com"
  ]
}
```

---

## Limitations & Disclaimer

- **Data source**: Results depend on what certificates have been logged in public CT logs and indexed by crt.sh, and on HackerTarget's database. Private/internal subdomains without public TLS certificates will not appear.
- **crt.sh instability**: crt.sh is a free service and is frequently slow or unavailable (502/503). The tool detects this automatically and falls back to HackerTarget. Use `--retries 5 --backoff 4.0` for slow connections.
- **HackerTarget rate limit**: Free tier is limited to 50 requests/day.
- **Passive recon only**: This tool does **not** perform DNS resolution, port scanning, or any active probing.
- **Legal**: Always obtain written permission before performing reconnaissance against systems you do not own. The authors are not responsible for misuse.

---

## Contributing

Pull requests are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests for new functionality
4. Ensure `pytest tests/ -v --cov=crtsh_recon --cov-fail-under=80` passes
5. Run `black --line-length=100 .` and `flake8 crtsh_recon/ main.py --max-line-length=100`
6. Submit a pull request