"""Shared pytest fixtures for Muninn tests."""

import pytest

from muninn.store import MuninnStore


@pytest.fixture
def store(tmp_path):
    """Return a MuninnStore backed by an isolated temporary SQLite database."""
    db_path = str(tmp_path / "test.db")
    return MuninnStore(db_path=db_path)
