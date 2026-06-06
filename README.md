# subhunt

> **Professional subdomain enumeration via Certificate Transparency logs & HackerTarget**

[![CI](https://github.com/ahmadouniass/subhunt/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmadouniass/subhunt/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`subhunt` is a modular, production-grade OSINT tool that harvests **subdomains** from multiple sources — [crt.sh](https://crt.sh) Certificate Transparency logs and [HackerTarget](https://hackertarget.com) — and merges the results automatically.

Designed for **bug bounty hunters**, **penetration testers**, and **security researchers** who need fast, reliable, repeatable subdomain enumeration as part of their reconnaissance workflow.

---

## Features

| Feature | Details |
|---|---|
| **Multi-source enumeration** | crt.sh + HackerTarget — merged & deduplicated automatically |
| **crt.sh health check** | Detects when crt.sh is down and falls back to HackerTarget |
| **Certificate Transparency** | `https://crt.sh/?q=%.domain&output=json` |
| **Wildcard cleaning** | Strips `*.` and `%.` prefixes, deduplicates, lowercases, scope-validates |
| **Multi-format export** | TXT (one per line), JSON (structured + metadata), CSV (indexed) |
| **Retry & timeout** | Exponential back-off via `urllib3` on 429/5xx |
| **Pretty terminal output** | Colour-coded results with animated spinner (via `colorama`) |
| **Verbose / debug mode** | Full DEBUG log to console and rotating log file under `logs/` |
| **Modular architecture** | Each concern in its own module — fully unit-tested |
| **pip-installable CLI** | `pip install .` registers the `subhunt` command globally |
| **167 unit tests** | Zero real network calls — all HTTP mocked, coverage ≥ 80% enforced in CI |

---

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/ahmadouniass/subhunt.git
cd subhunt
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
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
subhunt -d example.com
```

### crt.sh only

```bash
subhunt -d example.com --disable-hackertarget
```

### All export formats + verbose

```bash
subhunt -d example.com -f txt json csv -v
```

### Tuned network + custom output

```bash
subhunt -d example.com -f json csv -o /tmp/recon --timeout 60 --retries 5 --backoff 3.0
```

### Suppress banner (scripting / piping)

```bash
subhunt -d example.com --no-banner --no-file-log
```

### Full options

```
usage: subhunt [-h] -d DOMAIN [-f FORMAT [FORMAT ...]] [-o DIR]
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
  --disable-hackertarget       Use crt.sh only (HackerTarget enabled by default)

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
    3.  mail.example.com
    4.  vpn.example.com
    5.  www.example.com

  [*] Domain           : example.com
  [*] Cert records     : 312
  [*] Unique subdomains: 5
  [*] Elapsed time     : 2.41s

  [+] Done. 5 unique subdomain(s) found for example.com.
```

---

## Project Structure

```
subhunt/
├── main.py                        # CLI entry point (argparse)
├── subhunt/                       # Core package
│   ├── __init__.py
│   ├── client.py                  # crt.sh HTTP client (retry / health check)
│   ├── hackertarget_client.py     # HackerTarget API client
│   ├── parser.py                  # Extraction & cleaning
│   ├── validator.py               # Input validation
│   ├── exporter.py                # TXT / JSON / CSV writers
│   ├── scanner.py                 # Multi-source orchestrator
│   ├── display.py                 # Terminal output (colours, spinner)
│   ├── logger.py                  # Console + rotating file logger
│   └── exceptions.py             # Custom exception hierarchy
├── tests/
│   ├── conftest.py
│   ├── test_client.py             # 10 tests
│   ├── test_hackertarget.py       # 23 tests
│   ├── test_parser.py             # 19 tests
│   ├── test_validator.py          # 17 tests
│   ├── test_exporter.py           # 14 tests
│   ├── test_scanner.py            # 27 tests
│   ├── test_display.py            # 30 tests
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

## How It Works

1. **Health check** — `CRTClient.health_check()` pings crt.sh (5s timeout). If unreachable, the step is skipped automatically.
2. **crt.sh query** — `GET https://crt.sh/?q=%.{domain}&output=json` with retry-aware session.
3. **HackerTarget query** — `GET https://api.hackertarget.com/hostsearch/?q={domain}` (plain-text CSV).
4. **Parse & clean** — wildcards stripped (`*.` and `%.`), scope-filtered, lowercased, RFC-1123 validated.
5. **Merge & deduplicate** — results from both sources merged into a `set`, then sorted.
6. **Export** — timestamped files written under `output/`.
7. **Display** — colour-coded terminal output with spinner and summary.

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=subhunt --cov-report=term-missing --cov-fail-under=80
```

---

## JSON Output Schema

```json
{
  "meta": {
    "domain": "example.com",
    "total": 5,
    "generated_at": "2024-06-06T10:45:23+00:00",
    "tool": "subhunt",
    "cert_records_fetched": 312,
    "hackertarget_results": 3,
    "sources": ["crt.sh", "hackertarget"],
    "crtsh_available": true
  },
  "subdomains": [
    "api.example.com",
    "dev.example.com",
    "mail.example.com",
    "vpn.example.com",
    "www.example.com"
  ]
}
```

---

## Limitations & Disclaimer

- **crt.sh instability**: crt.sh is a free service, often slow or unavailable (502/503). The tool automatically detects this and switches to HackerTarget. Use `--retries 5 --backoff 4.0` on slow connections.  
- **HackerTarget rate limit**: Free tier limited to 50 requests/day.  
- **Passive recon only**: No DNS resolution, port scanning, or active probing.  
- **Legal**: Always obtain written authorization before performing reconnaissance on systems you do not own.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests for new functionality
4. Ensure `pytest tests/ -v --cov=subhunt --cov-fail-under=80` passes
5. Run `black --line-length=100 .` and `flake8 subhunt/ main.py --max-line-length=100`
6. Submit a pull request