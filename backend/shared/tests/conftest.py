"""Test fixtures for shared models."""

from datetime import datetime

import pytest


@pytest.fixture
def sample_timestamp():
    """Sample timestamp for testing."""
    return datetime(2025, 12, 9, 10, 30, 0)
