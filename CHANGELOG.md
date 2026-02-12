# Changelog

## [Unreleased] – branch `sandbox/jy/split_function` (2026-02-12)

### Added

- **Web UI 同源访问**：在 `serve` / `up` / `dev` 调用 backend 前，若存在兄弟目录 `Web-Service/static`，则设置环境变量 `WEB_UI_DIR` 指向该路径，使 backend 继续提供 `/` 与 `/static`，用户访问 http://localhost:8000 即可使用 Web UI（无需单独起 Web-Service 或改端口）。
- **短/中/长记忆配置与测试**（`tests/test_memory_stages_aura.py`）：验证 Aura 配置中 database（短期）、redis/minio（中期）、OSS 写入 backend app.yaml（长期）正确驱动三阶段记忆机制。

### Changed

- `_run_backend()` 中在委托给 agent-backend 前检测并注入 `WEB_UI_DIR`（路径：`<workspace>/Web-Service/static`，以 Aura-Swarm 为基准的兄弟目录）。
- **config/aura.yaml.example**：阿里云 OSS 注释说明配置后 Aura 启动时后端将使用 OSS 作为长时记忆存储。
