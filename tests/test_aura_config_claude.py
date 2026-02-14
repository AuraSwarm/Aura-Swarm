"""测试 Aura 配置中的 Claude API（anthropic_api_key / anthropic_base_url）是否生效。"""

import os
from pathlib import Path

import pytest
import yaml

from aura.config import AuraSettings, get_aura_settings, reset_aura_settings_cache


def test_aura_settings_to_backend_app_yaml_includes_anthropic():
    """Aura 中配置 anthropic_api_key / anthropic_base_url 时，生成给后端的 app 字典包含这两项。"""
    settings = AuraSettings.model_construct(
        anthropic_api_key="sk-ant-test-key",
        anthropic_base_url="https://gaccode.com/claudecode",
    )
    d = settings.to_backend_app_yaml_dict()
    assert "anthropic_api_key" in d
    assert d["anthropic_api_key"] == "sk-ant-test-key"
    assert "anthropic_base_url" in d
    assert d["anthropic_base_url"] == "https://gaccode.com/claudecode"


def test_aura_generated_app_yaml_claude_reachable_by_backend(tmp_path, monkeypatch):
    """Aura 生成 app.yaml 含 Claude 配置时，后端加载该配置后能读到 anthropic_api_key（即会生效）。"""
    app_yaml = tmp_path / "app.yaml"
    app_data = {
        "config_dir": str(tmp_path),
        "anthropic_api_key": "sk-ant-from-aura",
        "anthropic_base_url": "https://gaccode.com/claudecode",
    }
    with open(app_yaml, "w", encoding="utf-8") as f:
        yaml.dump(app_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    from app.config.loader import get_app_settings, reset_app_settings_cache

    reset_app_settings_cache()
    settings = get_app_settings()
    assert getattr(settings, "anthropic_api_key", None) == "sk-ant-from-aura"
    assert getattr(settings, "anthropic_base_url", None) == "https://gaccode.com/claudecode"


def test_aura_config_aura_yaml_claude_if_present():
    """若 config/aura.yaml 中已配置 Claude API，则 to_backend 输出中应包含并传递给后端。"""
    reset_aura_settings_cache()
    settings = get_aura_settings()
    d = settings.to_backend_app_yaml_dict()
    if getattr(settings, "anthropic_api_key", None) and settings.anthropic_api_key.strip():
        assert "anthropic_api_key" in d, "aura.yaml 中配置了 anthropic_api_key 时应写入后端 app 配置"
        assert d["anthropic_api_key"] == settings.anthropic_api_key.strip()
    if getattr(settings, "anthropic_base_url", None) and settings.anthropic_base_url.strip():
        assert "anthropic_base_url" in d, "aura.yaml 中配置了 anthropic_base_url 时应写入后端 app 配置"
        assert d["anthropic_base_url"] == settings.anthropic_base_url.strip()
