"""
logger.py — Centralised logging configuration for crtsh-recon.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

_CONSOLE_FORMAT = "%(message)s"
_FILE_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s:%(lineno)d  %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_ROOT_LOGGER = "subhunt"


def setup_logging(
    verbose: bool = False,
    log_dir: str = "logs",
    log_to_file: bool = True,
) -> None:
    """
    Configure the package-level logger.

    * Console handler: INFO (or DEBUG when *verbose* is True).
    * Rotating file handler: always DEBUG-level (10 MB, 3 back-ups).

    Args:
        verbose:     Enable DEBUG output on the console.
        log_dir:     Directory where log files are written.
        log_to_file: If False, skip file logging entirely.
    """
    root = logging.getLogger(_ROOT_LOGGER)
    root.setLevel(logging.DEBUG)  # allow everything through; handlers filter

    # Avoid adding duplicate handlers if called more than once
    if root.handlers:
        return

    console_level = logging.DEBUG if verbose else logging.INFO
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    root.addHandler(console_handler)

    if log_to_file:
        log_path = Path(log_dir)
        try:
            log_path.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_path / "subhunt.log",
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT))
            root.addHandler(file_handler)
        except (OSError, ValueError) as exc:
            root.warning("Could not create log file in %r: %s", log_dir, exc)


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger namespaced under the package root.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(f"{_ROOT_LOGGER}.{name}" if not name.startswith(_ROOT_LOGGER) else name)
