# Changelog

## [Unreleased] – branch `sandbox/jy/split_function`

### Added

- **Web UI 同源访问**：在 `serve` / `up` / `dev` 调用 backend 前，若存在兄弟目录 `Web-Service/static`，则设置环境变量 `WEB_UI_DIR` 指向该路径，使 backend 继续提供 `/` 与 `/static`，用户访问 http://localhost:8000 即可使用 Web UI（无需单独起 Web-Service 或改端口）。

### Changed

- `_run_backend()` 中在委托给 agent-backend 前检测并注入 `WEB_UI_DIR`（路径：`<workspace>/Web-Service/static`，以 Aura-Swarm 为基准的兄弟目录）。
