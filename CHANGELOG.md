# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-06-06

### Changed
- **Projet renommé `crtsh-recon` → `subhunt`** — le nom reflète désormais le périmètre réel de l'outil (multi-source, pas uniquement crt.sh)
- Package Python renommé `crtsh_recon/` → `subhunt/` — tous les imports mis à jour
- Commande CLI renommée `crtsh-recon` → `subhunt`
- `setup.py` : `name`, `entry_points` et `description` mis à jour
- `logger.py` : namespace de logging mis à jour (`subhunt`)
- User-Agent HTTP mis à jour dans `client.py` et `hackertarget_client.py`
- `README.md` et `CHANGELOG.md` mis à jour pour refléter le nouveau nom

---

## [1.1.0] - 2026-06-05

### Added
- **HackerTarget integration** — nouveau module `hackertarget_client.py` qui interroge `https://api.hackertarget.com/hostsearch/` et merge les résultats avec crt.sh
- **crt.sh health check** — `CRTClient.health_check()` détecte si crt.sh est down ; fallback automatique sur HackerTarget
- **`--disable-hackertarget` flag CLI** — opt-out HackerTarget pour un scan crt.sh uniquement
- **`HackerTargetClientError`** ajouté à la hiérarchie d'exceptions
- **`_parse_response()`** extrait comme fonction publique dans `hackertarget_client.py`
- **`hackertarget_count`** et **`crtsh_available`** ajoutés à `ScanResult`
- `test_hackertarget.py` — 23 tests unitaires
- `test_scanner.py` entièrement réécrit — 27 tests

### Changed
- `scanner.py` redesigné : health check → crt.sh → HackerTarget → merge → export
- `ScanConfig` : nouveau champ `use_hackertarget: bool = True`
- Export JSON enrichi : `hackertarget_results`, `sources`, `crtsh_available`
- `_strip_wildcard()` gère `*.` ET `%.` via `startswith`

### Fixed
- `logger.py` : `except (OSError, ValueError)` pour tous les OS
- CI : steps conditionnels par OS (fix PowerShell `\` line-continuation)
- flake8 F541 dans `main.py`
- Coverage `scanner.py` : 40% → 98%

---

## [1.0.0] - 2026-06-03

### Added
- Release initiale (`crtsh-recon`, renommé `subhunt` en v1.2.0)
- Énumération de sous-domaines via crt.sh Certificate Transparency logs
- Architecture modulaire : `client`, `parser`, `validator`, `exporter`, `scanner`, `display`, `logger`
- CLI argparse, export TXT/JSON/CSV, retry backoff, spinner colorama
- 117 tests unitaires, CI 3 OS × 3 Python, coverage gate 80%
- GitHub Release workflow, LICENSE MIT

---

## Unreleased

### Planned
- Source RapidDNS
- Résolution DNS des sous-domaines découverts
- PyPI release (`pip install subhunt`)