"""Overall tests: Aura launcher CLI (--help, --version, backend delegation, shortcuts)."""

import subprocess
import sys
from pathlib import Path

import pytest

# Run Aura via python -m so we don't depend on installed script
AURA_SWARM_ROOT = Path(__file__).resolve().parent.parent


def _run_aura(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "aura.cli"] + list(args),
        cwd=AURA_SWARM_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_aura_help():
    r = _run_aura("--help")
    assert r.returncode == 0
    assert "Aura Swarm" in r.stdout
    assert "backend" in r.stdout
    assert "serve" in r.stdout


def test_aura_version():
    r = _run_aura("--version")
    assert r.returncode == 0
    assert "0.1.0" in r.stdout.strip()


def test_aura_backend_serve_help():
    r = _run_aura("backend", "serve", "--help")
    assert r.returncode == 0
    assert "agent-backend" in r.stdout or "serve" in r.stdout
    assert "--reload" in r.stdout or "reload" in r.stdout


def test_aura_shortcut_serve_help():
    r = _run_aura("serve", "--help")
    assert r.returncode == 0
    assert "serve" in r.stdout and ("agent-backend" in r.stdout or "args" in r.stdout)


def test_aura_backend_version():
    r = _run_aura("backend", "version")
    assert r.returncode == 0
    assert r.stdout.strip()


def test_aura_shortcut_version():
    r = _run_aura("version")
    assert r.returncode == 0
    assert r.stdout.strip()


def test_aura_backend_init_db_help():
    r = _run_aura("backend", "init-db", "--help")
    assert r.returncode == 0
