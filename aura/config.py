"""
Unified config for Aura Swarm. Single source of truth; backend and other modules receive settings from here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

RunMode = Literal["node", "docker", "local"]


class AuraSettings(BaseModel):
    """Unified settings (config/aura.yaml). Used to generate backend app.yaml and drive up/down/serve."""

    model_config = {"extra": "ignore"}

    # --- Launcher ---
    run_mode: RunMode = Field("node", description="node | local | docker. node/local = ./run node|local; docker = compose up/down")

    # --- Server (backend) ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_backend"

    # --- Redis / MinIO ---
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "archives"

    # --- 阿里云 OSS (Memory-Base 长期存储，可选) ---
    oss_endpoint: str | None = Field(None, description="OSS endpoint, e.g. https://oss-cn-hangzhou.aliyuncs.com")
    oss_access_key_id: str | None = Field(None, description="Aliyun OSS AccessKey ID")
    oss_access_key_secret: str | None = Field(None, description="Aliyun OSS AccessKey Secret")
    oss_bucket: str | None = Field(None, description="OSS bucket name for long-term storage")

    # --- Config dir (for backend: where models.yaml lives; Aura injects this) ---
    config_dir: str = "config"

    # --- API / env (Qwen 使用 DashScope；token 可填 dashscope_api_key 或 qwen_token) ---
    dashscope_api_key: str | None = Field(None, description="DashScope API key (Qwen); also set via DASHSCOPE_API_KEY env")
    qwen_token: str | None = Field(None, description="Qwen/DashScope API token; used as dashscope_api_key when set")
    required_env_vars: list[str] = Field(default_factory=lambda: ["DASHSCOPE_API_KEY"])
    ai_env_path: str | None = Field(None, description="Path to env script for API keys; empty to disable")

    # --- ./run options ---
    skip_db_wait: bool = False
    no_db_password: bool = False
    use_local_postgres: bool = False
    dev: bool = False

    def get_oss_endpoint_normalized(self) -> str | None:
        """Return OSS endpoint with https:// if missing (oss2 需要完整 URL)."""
        ep = self.oss_endpoint
        if not ep or not ep.strip():
            return None
        ep = ep.strip().rstrip("/")
        if not ep.startswith("http://") and not ep.startswith("https://"):
            ep = "https://" + ep
        return ep

    def to_backend_app_yaml_dict(self) -> dict:
        """Dict suitable for backend config/app.yaml (and env substitution)."""
        d = self.model_dump(exclude_none=True)
        d["config_dir"] = "config"
        # OSS endpoint 规范化后写入 backend
        if self.oss_endpoint and self.oss_bucket:
            norm = self.get_oss_endpoint_normalized()
            if norm:
                d["oss_endpoint"] = norm
        # Backend 使用 dashscope_api_key；未设时用 qwen_token
        if not d.get("dashscope_api_key") and self.qwen_token:
            d["dashscope_api_key"] = self.qwen_token
        d.pop("qwen_token", None)
        return d


def ensure_backend_config_from_aura(backend_root: Path) -> str:
    """
    Write backend app.yaml from Aura settings and copy models.yaml; set CONFIG_DIR.
    Returns the CONFIG_DIR path (caller should set os.environ["CONFIG_DIR"] = returned path).
    """
    import shutil
    aura_root = Path(__file__).resolve().parent.parent
    generated = aura_root / ".aura" / "generated_config"
    generated.mkdir(parents=True, exist_ok=True)
    settings = get_aura_settings()
    app_data = settings.to_backend_app_yaml_dict()
    # Backend 用 config_dir 找 models.yaml，必须指向生成目录
    app_data["config_dir"] = str(generated)
    app_yaml_path = generated / "app.yaml"
    with open(app_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(app_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    for name in ("models.yaml", "models.yaml.example"):
        src = backend_root / "config" / name
        if src.exists():
            shutil.copy2(src, generated / name)
            break
    else:
        # No models file in backend (e.g. pip install without repo); write minimal so backend does not fail
        models_path = generated / "models.yaml"
        models_path.write_text(
            "local_tools: []\nembedding_providers: {}\nchat_providers: {}\nsummary_strategies: {}\n",
            encoding="utf-8",
        )
    return str(generated)


_aura_settings: AuraSettings | None = None


def _aura_config_path() -> Path:
    """Path to aura.yaml. AURA_CONFIG_DIR env or <Aura-Swarm-root>/config."""
    root = Path(__file__).resolve().parent.parent
    base = Path(os.environ.get("AURA_CONFIG_DIR", str(root / "config")))
    if not base.is_absolute():
        base = (root / base).resolve()
    return base / "aura.yaml"


def get_aura_settings() -> AuraSettings:
    """Load unified config from config/aura.yaml. Uses defaults when file missing."""
    global _aura_settings
    if _aura_settings is None:
        path = _aura_config_path()
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw) or {}
            # Simple ${VAR} substitution
            if isinstance(data, dict):
                data = _substitute_env(data)
            _aura_settings = AuraSettings.model_validate(data)
        else:
            _aura_settings = AuraSettings()
    return _aura_settings


def _substitute_env(obj: dict) -> dict:
    import re
    pattern = re.compile(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")

    def sub_val(val):
        if isinstance(val, str):
            return pattern.sub(lambda m: os.environ.get(m.group(1) or m.group(2) or "", m.group(0)), val)
        if isinstance(val, dict):
            return _substitute_env(val)
        if isinstance(val, list):
            return [sub_val(x) for x in val]
        return val

    return {k: sub_val(v) for k, v in obj.items()}
