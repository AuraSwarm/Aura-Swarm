"""Overall tests: Aura launcher CLI (--help, --version, backend delegation, shortcuts, cursor)."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

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
    assert "cursor" in r.stdout


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


# --- Cursor CLI support ---


def test_aura_cursor_help():
    """Aura cursor --help shows Cursor CLI subcommand help."""
    r = _run_aura("cursor", "--help")
    assert r.returncode == 0
    assert "cursor" in r.stdout.lower()
    assert "Cursor CLI" in r.stdout or "agent" in r.stdout.lower() or "workspace" in r.stdout.lower()


def test_aura_cursor_not_found():
    """When Cursor CLI (agent/cursor) is not in PATH, _run_cursor_cli returns 1 and stderr has install hint."""
    from aura.cli import _run_cursor_cli
    from io import StringIO

    with patch("aura.cli._cursor_cli_binary", return_value=None), patch(
        "sys.stderr", new_callable=StringIO
    ) as stderr:
        code = _run_cursor_cli(["--version"])
    assert code == 1
    err = stderr.getvalue()
    assert "Cursor CLI not found" in err
    assert "cursor.com" in err or "install" in err.lower()


def test_aura_cursor_invokes_binary():
    """_run_cursor_cli invokes Cursor CLI binary with given args and cwd=Aura root."""
    from aura.cli import _run_cursor_cli

    with patch("aura.cli._cursor_cli_binary", return_value="agent"), patch(
        "aura.cli.subprocess.run"
    ) as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(["agent", "--version"], returncode=0)
        code = _run_cursor_cli(["--version"])
    assert code == 0
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    call_kw = mock_run.call_args[1]
    assert call_args[0] == "agent"
    assert "--version" in call_args
    assert call_kw.get("cwd") == str(AURA_SWARM_ROOT)
