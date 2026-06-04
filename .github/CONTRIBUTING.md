# Contributing to crtsh-recon

Thank you for your interest in contributing to `crtsh-recon`! This document provides guidelines for development, testing, and submitting contributions.

---

## Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- pip (Python package manager)

### Clone & Install

```bash
git clone https://github.com/ahmadouniass/Subdomains-finder-crtsh.git
cd Subdomains-finder-crtsh
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Verify Installation

```bash
pytest tests/ -v
crtsh-recon --version
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage Report

```bash
pytest tests/ -v --cov=crtsh_recon --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest tests/test_parser.py -v
```

### Run Linting Checks

```bash
flake8 crtsh_recon/ main.py --max-line-length=100 --extend-ignore=E203,W503
black --check crtsh_recon/ main.py
```

### Auto-Format Code

```bash
black crtsh_recon/ main.py --line-length=100
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
   pytest tests/ -v --cov=crtsh_recon --cov-fail-under=80
   ```

2. **Format your code**
   ```bash
   black crtsh_recon/ main.py
   ```

3. **Check linting**
   ```bash
   flake8 crtsh_recon/ main.py --max-line-length=100 --extend-ignore=E203,W503
   ```

4. **Add tests for new features**
   - New functions should have corresponding unit tests
   - Aim for at least 80% coverage

### Required Coverage
- **Minimum 80%** test coverage across the codebase
- CI will fail if coverage drops below this threshold

---

## Project Structure

```
crtsh_recon/
├── __init__.py           # Package initialization
├── client.py             # HTTP client with retry logic
├── parser.py             # Subdomain extraction & cleaning
├── validator.py          # Input validation
├── exporter.py           # TXT/JSON/CSV export
├── scanner.py            # Orchestrator
├── display.py            # Terminal output
├── logger.py             # Logging configuration
└── exceptions.py         # Custom exceptions

tests/
├── test_client.py        # Client tests
├── test_parser.py        # Parser tests
├── test_validator.py     # Validator tests
├── test_exporter.py      # Exporter tests
├── test_logger.py        # Logger tests
├── test_display.py       # Display tests
└── __init__.py

main.py                    # CLI entry point
setup.py                   # Package configuration
requirements.txt           # Runtime dependencies
CHANGELOG.md              # Version history
```

---

## Making Changes

### Adding a New Feature

1. **Create a feature branch**
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Implement your feature** with tests

3. **Update CHANGELOG.md**
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

3. **Fix the bug**

4. **Verify the test passes**
   ```bash
   pytest tests/ -v
   ```

5. **Update CHANGELOG.md**
   ```markdown
   ## [Unreleased]

   ### Fixed
   - Bug description
   ```

6. **Push and create a PR**
   ```bash
   git push origin fix/bug-description
   ```

---

## Commit Message Guidelines

Use clear, descriptive commit messages:

- ✅ `feat: add multi-source fallback for crt.sh`
- ✅ `fix: handle null-byte paths on Windows`
- ✅ `docs: update README with examples`
- ✅ `test: add parser edge case tests`
- ❌ `fixed stuff`
- ❌ `update`

---

## Making a Release

### For Maintainers Only

1. **Update version in `setup.py`**
   ```python
   version="1.1.0",
   ```

2. **Update `CHANGELOG.md`**
   ```markdown
   ## [1.1.0] - 2024-06-15

   ### Added
   - Feature A
   - Feature B

   ### Fixed
   - Bug X
   ```

3. **Commit changes**
   ```bash
   git add setup.py CHANGELOG.md
   git commit -m "chore: bump version to 1.1.0"
   ```

4. **Create and push tag**
   ```bash
   git tag v1.1.0
   git push origin main
   git push origin v1.1.0
   ```

5. **GitHub Actions will automatically**
   - Run full test suite
   - Build `.tar.gz` and `.whl` distributions
   - Create a GitHub Release with artifacts
   - Publish to PyPI

---

## Reporting Issues

### Bug Reports
- Use the **Bug Report** issue template
- Include steps to reproduce
- Provide Python version and OS
- Attach relevant error logs

### Feature Requests
- Use the **Feature Request** issue template
- Describe the use case
- Explain why this feature would be helpful
- Suggest implementation approach if possible

---

## Questions?

- 📖 Check the [README](../README.md)
- 🐛 Search [existing issues](https://github.com/ahmadouniass/Subdomains-finder-crtsh/issues)
- 💬 Open a new discussion if you have questions

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for making `crtsh-recon` better! 🙏
