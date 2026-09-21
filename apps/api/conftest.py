# This conftest.py at the app level ensures pytest-asyncio is configured
import pytest

pytest_plugins = ("pytest_asyncio",)

def pytest_configure(config):
    """Set asyncio_mode to auto for the entire app."""
    config.option.asyncio_mode = "auto"
