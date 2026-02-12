# Aura Swarm

**Aura** is the unified launcher for Aura Swarm: one entry point for all components (backend, services, tools). Run `Aura --help` for the full command list.

## Install

From the workspace (with Memory-Base and Agent-Backend as siblings):

```bash
pip install -e ../Memory-Base
pip install -e ../Agent-Backend
pip install -e .
```

Check the launcher:

```bash
Aura --help
Aura --version
```

## Commands

### Unified config

All settings live in **one place**: **`config/aura.yaml`** (in Aura-Swarm). Create it with:

```bash
Aura configure   # creates config/aura.yaml from config/aura.yaml.example
```

Then edit `config/aura.yaml` (run_mode, database_url, host, port, etc.). Backend and other modules receive these settings; no need to configure each module separately.

### One-click

| Command | Description |
|---------|-------------|
| `Aura up` | One-click start (mode from config: **node** / **local** = DB + serve, **docker** = compose up) |
| `Aura dev` | One-click dev (node/local: same as up with --reload; docker: compose up) |
| `Aura down` | One-click stop (docker: compose stop; node/local: pkill backend) |
| `Aura configure` | Create config/aura.yaml from example if missing |

**run_mode** in `config/aura.yaml`: **`node`** (default) | **`local`** | **`docker`**.

### General

| Command | Description |
|---------|-------------|
| `Aura --help` | Show this launcher help |
| `Aura --version` | Aura Swarm launcher version |
| `Aura backend <cmd> [args...]` | Run agent-backend; e.g. `Aura backend serve --reload` |
| `Aura serve [args...]` | Shortcut: start API server (same as `Aura backend serve`) |
| `Aura init-db` | Shortcut: create DB extension and tables |
| `Aura test [args...]` | Shortcut: run backend tests (pytest) |
| `Aura version` | Shortcut: print backend version |
| `Aura health [--base-url URL]` | Shortcut: GET /health |
| `Aura configure` | Create config/aura.yaml from example (unified config) |
| `Aura start [SERVICE...]` | Shortcut: Docker Compose up |
| `Aura stop [SERVICE...]` | Shortcut: Docker Compose stop |
| `Aura restart [SERVICE...]` | Shortcut: Docker Compose restart |
| `Aura reload-config [--base-url URL]` | Shortcut: POST /admin/reload |
| `Aura archive` | Shortcut: run Celery archive task once |
| `Aura try-models [--prompt TEXT]` | Shortcut: call configured chat models |

For backend-specific options (e.g. `--host`, `--port`, `--real-api`, `--cov`), pass them after the command: `Aura serve --reload`, `Aura backend test --cov`. Full backend help: `Aura backend serve --help`, `Aura backend test --help`, etc.

## Examples

```bash
Aura configure            # Create config/aura.yaml (once)
# Edit config/aura.yaml: run_mode, database_url, port, ...
Aura up                   # One-click: mode from config (node/local = DB+serve, docker = compose up)
Aura dev                  # One-click dev (node/local: --reload)
Aura down                 # One-click stop
Aura serve --reload       # Start API server with auto-reload only
Aura init-db
Aura version
Aura backend serve --help
Aura test --cov
```

When `run_mode` is **node** or **local**, `Aura up`/`dev` require the Agent-Backend repo (with its `run` script). If the backend is installed without the repo, they fall back to `Aura serve` / `Aura serve --reload`. **Config is only in Aura**; do not configure backend or other modules separately.

## Testing

- **Module tests** — in each repo: `cd Agent-Backend && pytest tests/`, `cd Memory-Base && pytest tests/` (or `Aura backend test` for backend).
- **Overall tests** — in Aura-Swarm: `cd Aura-Swarm && pytest tests/` (launcher + optional run of module suites; requires workspace layout).

Launcher-only: `pytest tests/ -m "not module_integration"`.

## Adding entries

Add new subcommands in `aura/cli.py` and wire them to the corresponding CLIs or modules.
