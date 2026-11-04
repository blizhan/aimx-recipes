"""Pytest configuration and global fixtures for aimx-recipes tests."""

import json
from pathlib import Path
import shutil
import socket
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Ensure all tests run strictly offline with no external network access."""

    def fail_connect(*args, **kwargs):
        raise RuntimeError("Network access is prohibited during tests.")

    monkeypatch.setattr(socket.socket, "connect", fail_connect)
    monkeypatch.setattr(socket, "create_connection", fail_connect)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the absolute path to tests/fixtures."""
    return FIXTURES_DIR


@pytest.fixture
def load_fixture():
    """Helper fixture to load a JSON fixture relative to tests/fixtures."""

    def _loader(rel_path: str | Path):
        path = FIXTURES_DIR / rel_path
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return _loader


@pytest.fixture
def manifest(load_fixture) -> dict:
    """Return the loaded acceptance manifest."""
    return load_fixture("manifest.json")


@pytest.fixture
def kaggle_fixture_dir(tmp_path: Path) -> Path:
    """Copy tests/fixtures/kaggle/mini to a temporary directory for mutation."""
    dest = tmp_path / "meta-kaggle-mini"
    shutil.copytree(FIXTURES_DIR / "kaggle" / "mini", dest)
    return dest
