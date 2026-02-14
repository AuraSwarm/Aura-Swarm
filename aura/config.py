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

    # --- Ability 能力扩展（与 backend/local_tools 同构，同 id 覆盖） ---
    # 能力列表文件路径，相对 Aura 根目录；空或不设则用 config/abilities.yaml
    abilities_file: str | None = Field(None, description="Path to abilities YAML (relative to Aura root); default config/abilities.yaml. Gitignored when default.")

    # --- API / env (Qwen 使用 DashScope；token 可填 dashscope_api_key 或 qwen_token) ---
    dashscope_api_key: str | None = Field(None, description="DashScope API key (Qwen); also set via DASHSCOPE_API_KEY env")
    qwen_token: str | None = Field(None, description="Qwen/DashScope API token; used as dashscope_api_key when set")
    # Anthropic (Claude)：会传给后端 app.yaml，对应 ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL
    anthropic_api_key: str | None = Field(None, description="Anthropic API key; passed to backend as ANTHROPIC_API_KEY")
    anthropic_base_url: str | None = Field(None, description="Anthropic API base URL (e.g. https://gaccode.com/claudecode); passed to backend as ANTHROPIC_BASE_URL")
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


# 默认能力 config 内容（有效 YAML，local_tools 列表）
_DEFAULT_ABILITIES_CONF = """# Ability 仓库 config，由 Aura 自动生成。与 backend local_tools 同构。
# 编辑此文件后 Web 端「刷新能力列表」即可更新能力清单。

local_tools:
  - id: echo
    name: Echo
    description: Print a message to stdout
    command: ["echo", "{message}"]
  - id: date
    name: Date
    description: Print current date
    command: ["date"]
  - id: cursor
    name: Cursor CLI
    description: Run Cursor CLI (agent) with prompt. Requires Cursor CLI installed.
    command: ["agent", "-p", "{prompt}"]
  - id: copilot_cli
    name: Copilot CLI
    description: Run GitHub Copilot CLI with prompt. Requires @github/copilot.
    command: ["copilot", "-p", "{prompt}"]
  - id: claude
    name: Claude CLI
    description: Run Anthropic Claude CLI with prompt. Requires Claude Code installed.
    command: ["claude", "-p", "{prompt}"]
  - id: cursor_loop
    name: Cursor CLI (Loop)
    description: "Cursor CLI iterative; call multiple times for multi-turn. Param: prompt."
    command: ["agent", "-p", "{prompt}"]
  - id: copilot_cli_loop
    name: Copilot CLI (Loop)
    description: "Copilot CLI iterative; call multiple times for multi-turn. Param: prompt."
    command: ["copilot", "-p", "{prompt}"]
  - id: claude_loop
    name: Claude CLI (Loop)
    description: "Claude continue session (-c); append prompt to latest session. Param: prompt."
    command: ["claude", "-c", "-p", "{prompt}"]
"""


def _validate_abilities_config(path: Path) -> bool:
    """确保 path 是有效的 ability config（可解析且含 local_tools 列表或顶层列表）。"""
    if not path.exists():
        return False
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if data is None:
        return False
    if isinstance(data, list):
        return True
    if isinstance(data, dict) and isinstance(data.get("local_tools"), list):
        return True
    if isinstance(data, dict) and isinstance(data.get("abilities"), list):
        return True
    return False


def ensure_abilities_config(aura_root: Path) -> Path:
    """
    直接生成 ability 仓库对应 config（config/abilities.yaml），若不存在则从 example 复制或写入默认有效内容，并校验有效。
    返回生成的配置文件路径。
    """
    config_dir = aura_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    settings = get_aura_settings()
    rel = settings.abilities_file or "config/abilities.yaml"
    # 若为相对路径则相对于 Aura 根目录
    if Path(rel).is_absolute():
        ab_path = Path(rel)
    else:
        ab_path = (aura_root / rel).resolve()
    if ab_path.exists():
        if _validate_abilities_config(ab_path):
            return ab_path
        # 存在但无效，用默认覆盖
    example = config_dir / "abilities.yaml.example"
    ab_path.parent.mkdir(parents=True, exist_ok=True)
    if not ab_path.exists() and example.exists():
        ab_path.write_text(example.read_text(), encoding="utf-8")
    else:
        ab_path.write_text(_DEFAULT_ABILITIES_CONF, encoding="utf-8")
    if not _validate_abilities_config(ab_path):
        raise ValueError("Generated abilities config is invalid: %s" % ab_path)
    return ab_path


def _merge_abilities_into_generated(aura_root: Path, generated: Path) -> None:
    """
    Merge Aura config/abilities.yaml (if exists) into generated/models.yaml local_tools.
    Same id: Aura abilities override. File config/abilities.yaml is gitignored.
    """
    models_path = generated / "models.yaml"
    if not models_path.exists():
        return
    raw = models_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    base_tools = data.get("local_tools") or []
    by_id: dict = {}
    for t in base_tools:
        if isinstance(t, dict) and t.get("id"):
            by_id[t["id"]] = t
        elif hasattr(t, "id"):
            by_id[t.id] = {"id": t.id, "name": getattr(t, "name", t.id), "description": getattr(t, "description", ""), "command": getattr(t, "command", [])}
    abilities_rel = get_aura_settings().abilities_file or "config/abilities.yaml"
    abilities_path = (aura_root / abilities_rel).resolve() if not Path(abilities_rel).is_absolute() else Path(abilities_rel)
    if abilities_path.exists():
        ab_raw = abilities_path.read_text(encoding="utf-8")
        ab_data = yaml.safe_load(ab_raw)
        # Ability 仓库 config：支持 local_tools（与 models 同构）或顶层列表
        if isinstance(ab_data, list):
            ab_list = ab_data
        elif isinstance(ab_data, dict):
            ab_list = ab_data.get("local_tools") or ab_data.get("abilities") or []
        else:
            ab_list = []
        if isinstance(ab_list, list):
            for a in ab_list:
                if isinstance(a, dict) and a.get("id"):
                    by_id[a["id"]] = a
    data["local_tools"] = list(by_id.values())
    with open(models_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def ensure_backend_config_from_aura(backend_root: Path) -> str:
    """
    Write backend app.yaml from Aura settings and copy models.yaml; set CONFIG_DIR.
    先确保 ability 仓库 config（config/abilities.yaml）存在且有效，再合并进 generated models local_tools.
    Returns the CONFIG_DIR path (caller should set os.environ["CONFIG_DIR"] = returned path).
    """
    import shutil
    aura_root = Path(__file__).resolve().parent.parent
    ensure_abilities_config(aura_root)
    generated = aura_root / ".aura" / "generated_config"
    generated.mkdir(parents=True, exist_ok=True)
    settings = get_aura_settings()
    app_data = settings.to_backend_app_yaml_dict()
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
        models_path = generated / "models.yaml"
        models_path.write_text(
            "local_tools: []\nembedding_providers: {}\nchat_providers: {}\nsummary_strategies: {}\n",
            encoding="utf-8",
        )
    _merge_abilities_into_generated(aura_root, generated)
    # 使后端在 reload 时能重新读取 Aura 能力文件，Web 端刷新即可识别新增能力
    import os
    ab_rel = get_aura_settings().abilities_file or "config/abilities.yaml"
    ab_path = (aura_root / ab_rel).resolve() if not Path(ab_rel).is_absolute() else Path(ab_rel)
    os.environ["AURA_ABILITIES_FILE"] = str(ab_path)
    return str(generated)


_aura_settings: AuraSettings | None = None


def reset_aura_settings_cache() -> None:
    """Clear cached Aura settings. Next get_aura_settings() will reload from config/aura.yaml."""
    global _aura_settings
    _aura_settings = None


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
