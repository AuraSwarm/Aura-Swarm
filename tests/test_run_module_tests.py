"""Overall tests: run each module's test suite (requires workspace layout)."""

import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import AURA_SWARM_ROOT


def _workspace_root() -> Path | None:
    parent = AURA_SWARM_ROOT.parent
    if (parent / "Agent-Backend" / "pyproject.toml").exists():
        return parent
    return None


@pytest.mark.module_integration
def test_run_agent_backend_module_tests(workspace_root):
    """Run Agent-Backend module tests from Aura-Swarm (overall run). Requires workspace with Agent-Backend sibling."""
    if workspace_root is None:
        pytest.fail("Workspace layout required: run from workspace where Agent-Backend is sibling of Aura-Swarm")
    backend_root = workspace_root / "Agent-Backend"
    # Ignore tests that need real server/DB or have known async/mock issues when run in aggregate
    r = subprocess.run(
        [
            sys.executable, "-m", "pytest", "tests/", "-v",
            "--ignore=tests/test_integration_real_ai.py",
            "--ignore=tests/test_local_run_db.py",
            "--ignore=tests/test_main_api.py",
            "--ignore=tests/test_run.py",
        ],
        cwd=backend_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, (r.stdout or "") + (r.stderr or "")


@pytest.mark.module_integration
def test_run_memory_base_module_tests(workspace_root):
    """Run Memory-Base module tests from Aura-Swarm (overall run). Requires workspace with Memory-Base sibling."""
    if workspace_root is None:
        pytest.fail("Workspace layout required: run from workspace where Memory-Base is sibling of Aura-Swarm")
    mb_root = workspace_root / "Memory-Base"
    if not (mb_root / "tests").exists():
        pytest.fail("Memory-Base tests/ not found")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        cwd=mb_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, (r.stdout or "") + (r.stderr or "")
