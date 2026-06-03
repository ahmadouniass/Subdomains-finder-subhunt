"""
tests/test_logger.py — Unit tests for crtsh_recon.logger
"""

import logging
import pytest
from pathlib import Path
from unittest.mock import patch

from crtsh_recon.logger import setup_logging, get_logger, _ROOT_LOGGER


def _clear_handlers():
    """Remove all handlers from the root package logger between tests."""
    root = logging.getLogger(_ROOT_LOGGER)
    root.handlers.clear()


class TestSetupLogging:
    def setup_method(self):
        _clear_handlers()

    def test_adds_console_handler(self):
        setup_logging(log_to_file=False)
        root = logging.getLogger(_ROOT_LOGGER)
        assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)

    def test_default_level_is_info(self):
        setup_logging(log_to_file=False)
        root = logging.getLogger(_ROOT_LOGGER)
        console = next(h for h in root.handlers if isinstance(h, logging.StreamHandler))
        assert console.level == logging.INFO

    def test_verbose_sets_debug_level(self):
        setup_logging(verbose=True, log_to_file=False)
        root = logging.getLogger(_ROOT_LOGGER)
        console = next(h for h in root.handlers if isinstance(h, logging.StreamHandler))
        assert console.level == logging.DEBUG

    def test_root_logger_level_is_debug(self):
        setup_logging(log_to_file=False)
        root = logging.getLogger(_ROOT_LOGGER)
        assert root.level == logging.DEBUG

    def test_no_duplicate_handlers_on_double_call(self):
        setup_logging(log_to_file=False)
        setup_logging(log_to_file=False)
        root = logging.getLogger(_ROOT_LOGGER)
        assert len(root.handlers) == 1

    def test_file_handler_created(self, tmp_path):
        from logging.handlers import RotatingFileHandler
        setup_logging(log_dir=str(tmp_path), log_to_file=True)
        root = logging.getLogger(_ROOT_LOGGER)
        assert any(isinstance(h, RotatingFileHandler) for h in root.handlers)

    def test_log_file_exists_after_setup(self, tmp_path):
        setup_logging(log_dir=str(tmp_path), log_to_file=True)
        log_file = tmp_path / "crtsh_recon.log"
        assert log_file.exists()

    def test_no_file_handler_when_disabled(self):
        from logging.handlers import RotatingFileHandler
        setup_logging(log_to_file=False)
        root = logging.getLogger(_ROOT_LOGGER)
        assert not any(isinstance(h, RotatingFileHandler) for h in root.handlers)

    def test_invalid_log_dir_does_not_crash(self):
        # Should log a warning but not raise
        setup_logging(log_dir="/invalid/path/that/cannot/be/created\x00", log_to_file=True)


class TestGetLogger:
    def test_returns_logger_instance(self):
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_logger_name_namespaced(self):
        logger = get_logger("mymodule")
        assert _ROOT_LOGGER in logger.name

    def test_already_namespaced_not_doubled(self):
        logger = get_logger(f"{_ROOT_LOGGER}.mymodule")
        assert logger.name == f"{_ROOT_LOGGER}.mymodule"

    def test_child_loggers_propagate(self):
        setup_logging(log_to_file=False)
        _clear_handlers()
        setup_logging(log_to_file=False)
        logger = get_logger("child")
        assert logger.propagate is True
