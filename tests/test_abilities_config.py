"""Tests for ability repo config: abilities.yaml structure and CLI abilities (cursor, copilot_cli, claude)."""

import yaml
from pathlib import Path

import pytest

AURA_ROOT = Path(__file__).resolve().parent.parent
ABILITIES_YAML = AURA_ROOT / "config" / "abilities.yaml"
ABILITIES_EXAMPLE = AURA_ROOT / "config" / "abilities.yaml.example"

# CLI abilities (one-shot + loop) that must be present in the ability repo config
CLI_ABILITY_IDS = {"cursor", "copilot_cli", "claude", "cursor_loop", "copilot_cli_loop", "claude_loop"}


def _load_local_tools(path: Path) -> list[dict]:
    """Load local_tools list from YAML file."""
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return []
    if isinstance(data, dict):
        return data.get("local_tools") or data.get("abilities") or []
    if isinstance(data, list):
        return data
    return []


def test_abilities_yaml_exists_and_valid():
    """config/abilities.yaml exists and is valid YAML with local_tools list."""
    assert ABILITIES_YAML.exists(), "config/abilities.yaml should exist"
    tools = _load_local_tools(ABILITIES_YAML)
    assert isinstance(tools, list)
    for t in tools:
        assert isinstance(t, dict)
        assert "id" in t
        assert "name" in t
        assert "command" in t or "description" in t


def test_abilities_yaml_contains_cli_abilities():
    """config/abilities.yaml includes cursor, copilot_cli, claude as local_tools."""
    tools = _load_local_tools(ABILITIES_YAML)
    ids = {t["id"] for t in tools if isinstance(t, dict) and t.get("id")}
    for aid in CLI_ABILITY_IDS:
        assert aid in ids, f"abilities.yaml should contain ability id {aid!r}"


def test_abilities_yaml_cli_commands():
    """cursor, copilot_cli, claude and their _loop variants have command with {prompt}."""
    tools = _load_local_tools(ABILITIES_YAML)
    by_id = {t["id"]: t for t in tools if isinstance(t, dict) and t.get("id")}
    for aid in CLI_ABILITY_IDS:
        assert aid in by_id
        cmd = by_id[aid].get("command")
        assert cmd is not None, f"{aid} should have command"
        if isinstance(cmd, list):
            cmd_str = " ".join(cmd)
        else:
            cmd_str = str(cmd)
        assert "{prompt}" in cmd_str, f"{aid} command should accept {{prompt}}"


def test_abilities_yaml_claude_loop_uses_continue():
    """claude_loop uses -c (continue) for session persistence."""
    tools = _load_local_tools(ABILITIES_YAML)
    by_id = {t["id"]: t for t in tools if isinstance(t, dict) and t.get("id")}
    assert "claude_loop" in by_id
    cmd = by_id["claude_loop"].get("command")
    assert isinstance(cmd, list)
    assert "-c" in cmd


def test_default_abilities_conf_contains_cli_abilities():
    """Default generated abilities config (aura.config) includes CLI abilities and loop variants."""
    from aura.config import _DEFAULT_ABILITIES_CONF

    data = yaml.safe_load(_DEFAULT_ABILITIES_CONF)
    assert data is not None
    tools = data.get("local_tools") or []
    ids = {t["id"] for t in tools if isinstance(t, dict) and t.get("id")}
    for aid in CLI_ABILITY_IDS:
        assert aid in ids, f"_DEFAULT_ABILITIES_CONF should contain {aid!r}"


def test_abilities_yaml_example_contains_cli_abilities():
    """config/abilities.yaml.example documents cursor, copilot_cli, claude."""
    assert ABILITIES_EXAMPLE.exists()
    tools = _load_local_tools(ABILITIES_EXAMPLE)
    ids = {t["id"] for t in tools if isinstance(t, dict) and t.get("id")}
    for aid in CLI_ABILITY_IDS:
        assert aid in ids, f"abilities.yaml.example should contain {aid!r}"
