"""Tests for logging configuration."""

import json
import logging
import tempfile
from pathlib import Path

from cafe_order_api.logger import JSONFormatter, get_uvicorn_config, setup_logging


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_format_with_exception(self):
        """Test formatting a log record with exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "Test error" in data["exception"]

    def test_format_with_args(self):
        """Test formatting a log record with message arguments."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Value is %s",
            args=("hello",),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["message"] == "Value is hello"


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_creates_directory(self):
        """Test that setup_logging creates the log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "test.log"

            setup_logging(str(log_file))

            assert log_file.parent.exists()

    def test_setup_logging_creates_file(self):
        """Test that setup_logging creates the log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            setup_logging(str(log_file))

            assert log_file.exists()

    def test_setup_logging_configures_handlers(self):
        """Test that setup_logging configures console and file handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            # Clear any existing handlers
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

            setup_logging(str(log_file))

            root_logger = logging.getLogger()
            handler_types = [type(h).__name__ for h in root_logger.handlers]

            assert "StreamHandler" in handler_types
            assert "FileHandler" in handler_types

    def test_setup_logging_removes_duplicate_handlers(self):
        """Test that setup_logging removes existing handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            # Call setup_logging twice
            setup_logging(str(log_file))
            initial_count = len(logging.getLogger().handlers)

            setup_logging(str(log_file))
            final_count = len(logging.getLogger().handlers)

            # Should have same number of handlers (old ones removed)
            assert final_count == initial_count


class TestGetUvicornConfig:
    """Tests for get_uvicorn_config function."""

    def test_returns_dict(self):
        """Test that get_uvicorn_config returns a dictionary."""
        config = get_uvicorn_config()

        assert isinstance(config, dict)

    def test_has_required_keys(self):
        """Test that config has required logging config keys."""
        config = get_uvicorn_config()

        assert "version" in config
        assert "formatters" in config
        assert "handlers" in config
        assert "loggers" in config

    def test_has_json_formatter(self):
        """Test that config includes JSON formatter."""
        config = get_uvicorn_config()

        assert "json" in config["formatters"]
        assert config["formatters"]["json"]["()"] == JSONFormatter

    def test_configures_uvicorn_loggers(self):
        """Test that config includes uvicorn logger configurations."""
        config = get_uvicorn_config()

        assert "uvicorn" in config["loggers"]
        assert "uvicorn.access" in config["loggers"]
        assert "uvicorn.error" in config["loggers"]
