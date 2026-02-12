"""
Tests that Aura config drives short / medium / long term memory mechanisms.

- Short: database_url in config (sessions + messages).
- Medium: redis_url, minio_* in config (archive / summarization).
- Long: when oss_* is set, backend app.yaml receives OSS so long-term storage uses Aliyun.
"""

import pytest

from aura.config import get_aura_settings


def test_short_term_memory_aura_config_has_database():
    """Short-term: Aura config provides database_url for session/message storage."""
    settings = get_aura_settings()
    assert settings.database_url
    assert "postgresql" in settings.database_url or "asyncpg" in settings.database_url


def test_medium_term_memory_aura_config_has_archive():
    """Medium-term: Aura config provides redis and minio for archive/summary pipeline."""
    settings = get_aura_settings()
    assert settings.redis_url
    assert settings.minio_endpoint
    assert settings.minio_bucket


def test_long_term_memory_aura_config_oss_in_backend_yaml():
    """Long-term: when OSS is configured, backend app.yaml dict includes oss_* so backend uses Aliyun."""
    settings = get_aura_settings()
    backend_dict = settings.to_backend_app_yaml_dict()
    if settings.oss_endpoint and settings.oss_bucket and settings.oss_access_key_id and settings.oss_access_key_secret:
        assert backend_dict.get("oss_endpoint")
        assert backend_dict.get("oss_bucket") == settings.oss_bucket
        assert backend_dict.get("oss_access_key_id")
        assert backend_dict.get("oss_access_key_secret")
    else:
        # No OSS in aura.yaml: backend gets no oss_* and uses in-memory long-term
        assert backend_dict.get("oss_endpoint") is None or backend_dict.get("oss_bucket") is None
