# crtsh-recon

> **Professional subdomain enumeration via Certificate Transparency logs**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: PEP8](https://img.shields.io/badge/code%20style-PEP8-orange.svg)](https://peps.python.org/pep-0008/)

`crtsh-recon` is a modular, production-grade OSINT tool that harvests **subdomains** from [crt.sh](https://crt.sh) — a public archive of SSL/TLS certificate transparency logs maintained by Sectigo.  
It is designed for **bug bounty hunters**, **penetration testers**, and **security researchers** who need fast, reliable, repeatable subdomain enumeration as part of their reconnaissance workflow.

---

## Features

| Feature | Details |
|---|---|
| **Certificate Transparency query** | Queries `https://crt.sh/?q=%.domain&output=json` |
| **Wildcard & duplicate cleaning** | Strips `*.` prefixes, deduplicates, lowercases |
| **Multi-format export** | TXT (one per line), JSON (structured + metadata), CSV (indexed) |
| **Retry & timeout handling** | Exponential back-off via `urllib3.util.retry.Retry` |
| **Pretty terminal output** | Colour-coded results with spinner progress indicator |
| **Verbose / debug mode** | Full DEBUG log to console and rotating log file |
| **Modular architecture** | Client / Parser / Validator / Exporter / Display — fully unit-tested |
| **pip-installable CLI** | `pip install .` registers the `crtsh-recon` command globally |

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

### Basic scan

```bash
crtsh-recon -d example.com
```

### All export formats

```bash
crtsh-recon -d example.com -f txt json csv
```

### Custom output directory + verbose

```bash
crtsh-recon -d example.com -f json csv -o /tmp/recon -v
```

### Tune network settings (slow / unreliable connections)

```bash
crtsh-recon -d example.com --timeout 60 --retries 5 --backoff 3.0
```

### Suppress banner (scripting / piping)

```bash
crtsh-recon -d example.com --no-banner --no-file-log
```

### Full options

```
usage: crtsh-recon [-h] -d DOMAIN [-f FORMAT [FORMAT ...]] [-o DIR]
                   [--no-export] [--timeout SEC] [--retries N]
                   [--backoff FACTOR] [-v] [--log-dir DIR] [--no-file-log]
                   [--version] [--no-banner]

target:
  -d, --domain DOMAIN          Apex domain to enumerate (e.g. example.com)

output:
  -f, --formats FORMAT ...     Export format(s): txt json csv  (default: txt)
  -o, --output-dir DIR         Output directory               (default: ./output)
  --no-export                  Skip file export; print results only

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
  ██████╗██████╗ ████████╗  ███████╗██╗  ██╗  ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗
  ...

  v1.0.0  |  Certificate Transparency Subdomain Recon

  [*] Target domain   : example.com
  [*] Export formats  : txt, json, csv
  [*] Output directory: output
  [*] Timeout / Retries: 30s / 3

  ⠸  Querying crt.sh for *.example.com

  ────────────────────────────────────────────────────────────
    Results for example.com
  ────────────────────────────────────────────────────────────
    1.  api.example.com
    2.  dev.example.com
    3.  example.com
    4.  mail.example.com
    5.  staging.example.com
    6.  www.example.com

  ────────────────────────────────────────────────────────────
    Summary
  ────────────────────────────────────────────────────────────
  [*] Domain           : example.com
  [*] Cert records     : 312
  [*] Unique subdomains: 6
  [*] Elapsed time     : 1.84s

  [*] Exported files:
       TXT:  output/example.com_20240315_104523.txt
       JSON: output/example.com_20240315_104523.json
       CSV:  output/example.com_20240315_104523.csv

  [+] Done. 6 unique subdomain(s) found for example.com.
```

---

## Project Structure

```
crtsh-recon/
│
├── main.py                    # CLI entry point (argparse)
│
├── crtsh_recon/               # Core package
│   ├── __init__.py            # Public API + version
│   ├── client.py              # CRT.sh HTTP client (retry / timeout)
│   ├── parser.py              # Subdomain extraction & cleaning
│   ├── validator.py           # Input validation (domain, formats)
│   ├── exporter.py            # TXT / JSON / CSV writers
│   ├── scanner.py             # Orchestrator (ties all modules together)
│   ├── display.py             # Terminal output (colours, spinner, tables)
│   ├── logger.py              # Logging configuration (console + file)
│   └── exceptions.py          # Custom exception hierarchy
│
├── tests/
│   ├── __init__.py
│   ├── test_client.py         # Client unit tests (mocked HTTP)
│   ├── test_parser.py         # Parser unit tests
│   ├── test_validator.py      # Validator unit tests
│   └── test_exporter.py       # Exporter unit tests
│
├── output/                    # Default results directory (git-ignored)
├── logs/                      # Rotating log files (git-ignored)
│
├── requirements.txt
├── setup.py                   # pip install / CLI registration
├── .gitignore
└── README.md
```

---

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=crtsh_recon --cov-report=term-missing
```

---

## How It Works

1. **Query** — The `CRTClient` sends `GET https://crt.sh/?q=%.{domain}&output=json` with a retry-aware session.
2. **Parse** — `extract_subdomains()` iterates every cert record, splits multi-value `name_value` fields, strips wildcard prefixes, validates syntax, and discards out-of-scope names.
3. **Deduplicate & sort** — A `set` eliminates duplicates; the final list is sorted alphabetically.
4. **Export** — `export_results()` dispatches to the requested writer(s) and saves timestamped files under `output/`.
5. **Display** — `display.py` renders the results and summary to the terminal with ANSI colours (via `colorama`) and a non-blocking spinner.

---

## JSON Output Schema

```json
{
  "meta": {
    "domain": "example.com",
    "total": 6,
    "generated_at": "2024-03-15T10:45:23+00:00",
    "tool": "crtsh-recon",
    "cert_records_fetched": 312,
    "retries_configured": 3
  },
  "subdomains": [
    "api.example.com",
    "dev.example.com",
    "example.com",
    "mail.example.com",
    "staging.example.com",
    "www.example.com"
  ]
}
```

---

## Limitations & Disclaimer

- **Data source**: Results depend entirely on what certificates have been logged in public CT logs and indexed by crt.sh. Private/internal subdomains that have never received a public TLS certificate will not appear.
- **Rate limiting**: crt.sh may throttle heavy usage. Use `--retries` and `--backoff` to handle transient failures gracefully.
- **Passive recon only**: This tool does **not** perform DNS resolution, port scanning, or any active probing. It queries only the public crt.sh API.
- **Legal**: Always obtain written permission before performing reconnaissance against systems you do not own. The authors are not responsible for misuse.

---

## Contributing

Pull requests are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests for new functionality
4. Ensure `pytest tests/ -v` passes
5. Submit a pull request

---

## Disclaimer

The crt.sh website is often down, so errors may occur frequently. We are also exploring the possibility of adding other sources, so feel free to suggest some to us.