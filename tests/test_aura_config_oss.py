"""Tests that use Aura config (config/aura.yaml): OSS endpoint normalization and optional real OSS API."""

import uuid

import pytest

from aura.config import get_aura_settings


def test_aura_settings_loads_oss_from_config():
    """Aura 配置加载后 oss_* 字段可从 config/aura.yaml 读取."""
    settings = get_aura_settings()
    # 若 aura.yaml 中配置了 OSS，则应有 endpoint/bucket
    if settings.oss_bucket and settings.oss_endpoint:
        assert settings.oss_bucket.strip() == "aura-mem"
        norm = settings.get_oss_endpoint_normalized()
        assert norm is not None
        assert norm.startswith("https://") or norm.startswith("http://")


def test_oss_endpoint_normalized_adds_https():
    """get_oss_endpoint_normalized 对无 scheme 的 endpoint 补 https://."""
    from aura.config import AuraSettings

    # 使用临时实例，不污染全局 get_aura_settings() 缓存
    no_scheme = AuraSettings.model_construct(oss_endpoint="oss-cn-hangzhou.aliyuncs.com", oss_bucket="b")
    norm = no_scheme.get_oss_endpoint_normalized()
    assert norm == "https://oss-cn-hangzhou.aliyuncs.com"

    with_scheme = AuraSettings.model_construct(oss_endpoint="https://oss-cn-beijing.aliyuncs.com", oss_bucket="b")
    norm = with_scheme.get_oss_endpoint_normalized()
    assert norm == "https://oss-cn-beijing.aliyuncs.com"


@pytest.mark.real_oss
def test_oss_real_api_using_aura_config():
    """使用 Aura 配置中的 OSS 凭证调用真实阿里云 OSS API（需 oss2 与 aura.yaml 中 oss_* 已配置）."""
    try:
        from memory_base.long_term_storage import OssStorage
    except ImportError:
        pytest.skip("memory_base not installed")

    try:
        import oss2  # noqa: F401
    except ImportError:
        pytest.skip("oss2 not installed; pip install oss2 or pip install memory-base[oss]")

    settings = get_aura_settings()
    endpoint = settings.get_oss_endpoint_normalized()
    if not all([endpoint, settings.oss_access_key_id, settings.oss_access_key_secret, settings.oss_bucket]):
        pytest.skip("Aura config has no OSS credentials (oss_endpoint, oss_access_key_id, oss_access_key_secret, oss_bucket)")

    backend = OssStorage(
        bucket=settings.oss_bucket,
        access_key_id=settings.oss_access_key_id,
        access_key_secret=settings.oss_access_key_secret,
        endpoint=endpoint,
    )

    prefix = f"aura_test/{uuid.uuid4().hex}/"
    key1 = prefix + "profiles/aura_user.json"
    key2 = prefix + "knowledge/aura_user.jsonl"
    body1 = '{"traits": {"from": "aura_config_test"}}'
    body2 = "line1\nline2\n"

    try:
        backend.put_object(key1, body1, content_type="application/json")
        backend.put_object(key2, body2)
    except Exception as e:
        if getattr(e, "status", None) == 403 or "AccessDenied" in type(e).__name__:
            pytest.skip(
                "OSS 返回 403 AccessDenied：请检查 bucket ACL 或 RAM 用户是否具备该 bucket 的读写权限。"
            )
        raise

    out1 = backend.get_object(key1)
    assert out1 is not None
    assert out1.decode("utf-8") == body1
    out2 = backend.get_object(key2)
    assert out2 is not None
    assert out2.decode("utf-8") == body2

    keys = backend.list_prefix(prefix)
    assert set(keys) == {key1, key2}

    def _skip_403(msg="OSS 返回 403：请检查 bucket ACL 或 RAM 用户是否具备该 bucket 的读写删权限。"):
        pytest.skip(msg)

    try:
        backend.delete_object(key1)
        backend.delete_object(key2)
    except Exception as e:
        if getattr(e, "status", None) == 403 or "AccessDenied" in type(e).__name__:
            _skip_403()
        raise
    assert backend.get_object(key1) is None
    assert backend.get_object(key2) is None
    assert backend.list_prefix(prefix) == []
