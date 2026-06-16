# Contributing to subhunt

Thank you for your interest in contributing to `subhunt`! This document provides guidelines for development, testing, and submitting contributions.

---

## Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- pip (Python package manager)

### Clone & Install

```bash
git clone https://github.com/ahmadouniass/subhunt.git
cd subhunt
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Verify Installation

```bash
pytest tests/ -v
subhunt --version
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage Report

```bash
pytest tests/ -v --cov=subhunt --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest tests/test_parser.py -v
```

### Run Linting Checks

```bash
flake8 subhunt/ main.py --max-line-length=100 --extend-ignore=E203,W503
black --check --diff --line-length=100 subhunt/ main.py
```

### Auto-Format Code

```bash
black --line-length=100 subhunt/ main.py
```

---

## Code Standards

### Style Guide
- **PEP 8** compliance (enforced via `flake8`)
- **Black formatting** (enforced via `black`)
- Max line length: **100 characters**
- Docstrings on all public functions and classes

### Before Submitting a PR

1. **Run tests locally**
   ```bash
   pytest tests/ -v --cov=subhunt --cov-fail-under=80
   ```

2. **Format your code**
   ```bash
   black --line-length=100 subhunt/ main.py
   ```

3. **Check linting**
   ```bash
   flake8 subhunt/ main.py --max-line-length=100 --extend-ignore=E203,W503
   ```

4. **Add tests for new features**
   - New functions must have corresponding unit tests
   - No real network calls in tests — mock all HTTP with `unittest.mock`
   - Aim for at least **80% coverage** on new modules

### Required Coverage
- **Minimum 80%** test coverage across the codebase
- CI will fail if coverage drops below this threshold

---

## Project Structure

```
subhunt/
├── __init__.py               # Package initialization & version
├── client.py                 # crt.sh HTTP client (retry / health check)
├── hackertarget_client.py    # HackerTarget API client
├── rapiddns_client.py        # RapidDNS HTML scraper
├── parser.py                 # Subdomain extraction & cleaning
├── validator.py              # Input validation
├── exporter.py               # TXT / JSON / CSV export
├── scanner.py                # Multi-source orchestrator
├── display.py                # Terminal output (colours, spinner)
├── logger.py                 # Logging configuration
└── exceptions.py             # Custom exception hierarchy

tests/
├── conftest.py               # Shared fixtures
├── test_client.py            # crt.sh client tests
├── test_hackertarget.py      # HackerTarget client tests
├── test_rapiddns.py          # RapidDNS client tests
├── test_parser.py            # Parser tests
├── test_validator.py         # Validator tests
├── test_exporter.py          # Exporter tests
├── test_scanner.py           # Orchestrator tests
├── test_display.py           # Display tests
├── test_logger.py            # Logger tests
└── __init__.py

main.py                       # CLI entry point
setup.py                      # Package configuration
requirements.txt              # Runtime dependencies
CHANGELOG.md                  # Version history
```

---

## Adding a New Enumeration Source

`subhunt` is designed to be extended with new sources easily. Here's how to add one:

1. **Create `subhunt/mysource_client.py`**
   - Follow the same pattern as `hackertarget_client.py` or `rapiddns_client.py`
   - Implement `fetch_subdomains(domain) -> set[str]`
   - Use `_build_session()` with retry strategy
   - Add a dedicated exception in `exceptions.py`

2. **Update `subhunt/scanner.py`**
   - Add `use_mysource: bool = True` to `ScanConfig`
   - Add the fetch block in `run_scan()` after existing sources

3. **Update `main.py`**
   - Add `--disable-mysource` flag in the `sources` group
   - Pass `use_mysource=not args.disable_mysource` to `ScanConfig`

4. **Write tests in `tests/test_mysource.py`**
   - Mock all HTTP calls via `patch.object(client.session, "get", ...)`
   - Cover: success, empty response, 429, 5xx, connection error, timeout

5. **Update docs**
   - Add the new source to `README.md` features table
   - Add an entry in `CHANGELOG.md` under `## [Unreleased]`

---

## Making Changes

### Adding a New Feature

1. **Create a feature branch**
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Implement your feature** with tests

3. **Update `CHANGELOG.md`**
   ```markdown
   ## [Unreleased]

   ### Added
   - New feature description
   ```

4. **Push and create a PR**
   ```bash
   git push origin feat/my-feature
   ```

### Fixing a Bug

1. **Create a bugfix branch**
   ```bash
   git checkout -b fix/bug-description
   ```

2. **Add a test that reproduces the bug**

3. **Fix the bug and verify the test passes**
   ```bash
   pytest tests/ -v
   ```

4. **Update `CHANGELOG.md`**
   ```markdown
   ## [Unreleased]

   ### Fixed
   - Bug description
   ```

5. **Push and create a PR**
   ```bash
   git push origin fix/bug-description
   ```

---

## Commit Message Guidelines

Use clear, descriptive commit messages following the Conventional Commits format:

- ✅ `feat: add RapidDNS as third enumeration source`
- ✅ `fix: handle null-byte paths on Windows in logger`
- ✅ `docs: update README with multi-source usage examples`
- ✅ `test: add scanner fallback tests for crt.sh down scenario`
- ✅ `refactor: rename package crtsh_recon → subhunt`
- ✅ `chore: bump version to 1.3.0`
- ❌ `fixed stuff`
- ❌ `update`

---

## Making a Release

### For Maintainers Only

1. **Update version in `setup.py` and `subhunt/__init__.py`**
   ```python
   version="1.3.0"
   __version__ = "1.3.0"
   ```

2. **Update `CHANGELOG.md`**
   ```markdown
   ## [1.3.0] - YYYY-MM-DD

   ### Added
   - Feature A

   ### Fixed
   - Bug X
   ```

3. **Commit and tag**
   ```bash
   git add setup.py subhunt/__init__.py CHANGELOG.md
   git commit -m "chore: bump version to 1.3.0"
   git tag v1.3.0
   git push origin main
   git push origin v1.3.0
   ```

4. **GitHub Actions will automatically**
   - Run the full test suite (3 OS × 3 Python versions)
   - Build `.tar.gz` and `.whl` distributions
   - Create a GitHub Release with release notes from `CHANGELOG.md`

---

## Reporting Issues

### Bug Reports
- Use the **Bug Report** issue template
- Include steps to reproduce
- Provide Python version and OS
- Attach relevant error logs from `logs/subhunt.log`

### Feature Requests
- Use the **Feature Request** issue template
- Describe the use case
- Explain why this feature would be helpful for OSINT / bug bounty workflows
- Suggest implementation approach if possible

---

## Questions?

- 📖 Check the [README](README.md)
- 🐛 Search [existing issues](https://github.com/ahmadouniass/subhunt/issues)
- 💬 Open a new discussion if you have questions

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for making `subhunt` better! 🙏