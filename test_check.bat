@echo off

echo Running flake8...
flake8 subhunt/ main.py --max-line-length=100 --extend-ignore=E203,W503
if errorlevel 1 exit /b 1

echo Running black...
black --check --diff --line-length=100 subhunt/ main.py
if errorlevel 1 exit /b 1

REM potentiel solve en cas d'erreur de black :
REM black --line-length=100 subhunt/scanner.py main.py



echo Running tests...
pytest tests/ -v --tb=short --cov=subhunt --cov-fail-under=80
if errorlevel 1 exit /b 1

echo All checks passed!