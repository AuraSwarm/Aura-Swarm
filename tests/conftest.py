"""Pytest config for Aura Swarm overall tests."""

import subprocess
import sys
from pathlib import Path

import pytest

# Root of Aura-Swarm repo
AURA_SWARM_ROOT = Path(__file__).resolve().parent.parent


def _workspace_root() -> Path | None:
    """Parent of Aura-Swarm is the workspace (Agent-Backend, Memory-Base siblings)."""
    parent = AURA_SWARM_ROOT.parent
    if (parent / "Agent-Backend" / "pyproject.toml").exists():
        return parent
    return None


@pytest.fixture(scope="session")
def workspace_root():
    """Workspace root (parent of Aura-Swarm) when running in workspace layout."""
    return _workspace_root()
