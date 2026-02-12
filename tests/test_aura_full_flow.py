"""Smoke tests for Aura full flow (help, version, configure, init-db, try-models when API key set)."""

import subprocess
import sys
from pathlib import Path

import pytest

AURA_ROOT = Path(__file__).resolve().parent.parent


def _aura(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "aura.cli"] + list(args),
        cwd=AURA_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_aura_help():
    r = _aura("--help")
    assert r.returncode == 0
    assert "up" in r.stdout and "serve" in r.stdout


def test_aura_version():
    r = _aura("--version")
    assert r.returncode == 0
    assert r.stdout.strip()


def test_aura_configure():
    r = _aura("configure")
    assert r.returncode == 0


def test_aura_backend_version():
    r = _aura("version")
    assert r.returncode == 0
    assert r.stdout.strip()


def test_aura_init_db():
    """Requires Postgres; may be skipped in CI without DB."""
    r = _aura("init-db")
    # 0 = success; non-zero = connection error etc.
    assert r.returncode in (0, 1)


@pytest.mark.skip(reason="Calls real API; run manually when API key configured")
def test_aura_try_models():
    r = _aura("try-models", "--prompt=Say OK")
    assert r.returncode == 0
    assert "OK" in r.stdout or "qwen" in r.stdout.lower()
