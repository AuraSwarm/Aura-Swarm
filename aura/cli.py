"""
Aura — unified launcher for Aura Swarm.

  Aura up                      One-click start (DB + backend via backend's ./run node)
  Aura dev                     One-click dev (same as up with --reload)
  Aura down                    One-click stop (Docker / backend stop)
  Aura backend <cmd> [args...] Run agent-backend (serve, init-db, test, start, stop, ...)
  Aura serve [args...]         Shortcut: start API server
  Aura --help                  Show this help; Aura backend <cmd> --help for backend options
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from aura import __version__


def _backend_root() -> Path:
    """Agent-Backend repo root (parent of app/)."""
    import app
    return Path(app.__file__).resolve().parent.parent


def _run_backend(argv: list[str]) -> NoReturn:
    """Delegate to agent-backend CLI; inject Aura config so backend uses unified settings."""
    _inject_aura_config()
    # When Web-Service/static exists (sibling of Aura-Swarm), serve UI from there so GET / works
    _aura_root = Path(__file__).resolve().parent.parent
    _web_static = _aura_root.parent / "Web-Service" / "static"
    if _web_static.is_dir():
        os.environ["WEB_UI_DIR"] = str(_web_static)
    from app.cli import main as agent_backend_main
    sys.argv = ["agent-backend"] + argv
    sys.exit(agent_backend_main())


def _inject_aura_config() -> None:
    """Ensure backend receives config from Aura (config/aura.yaml); set CONFIG_DIR."""
    root = _backend_root()
    from aura.config import ensure_backend_config_from_aura
    os.environ["CONFIG_DIR"] = ensure_backend_config_from_aura(root)


def _get_run_mode() -> str:
    """Read run_mode from Aura unified config (config/aura.yaml). node | local | docker."""
    from aura.config import get_aura_settings
    return get_aura_settings().run_mode or "node"


def _run_run_script(mode: str, env_extra: dict | None = None) -> int:
    """Run backend's ./run script (one-click: DB + serve). Returns exit code."""
    _inject_aura_config()
    root = _backend_root()
    run_script = root / "run"
    if not run_script.is_file():
        # Fallback when backend is installed without repo (e.g. from pip)
        if mode == "node" or mode == "local":
            _run_backend(["serve"])
        else:
            _run_backend(["serve", "--reload"])
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(run_script), mode],
        cwd=str(root),
        env=env,
    ).returncode


_EPILOG = """
Examples:
  Aura up                      One-click start (run_mode in config: node | local | docker)
  Aura dev                     One-click dev (node/local: --reload; docker: start)
  Aura down                    One-click stop (docker: compose stop; node/local: pkill backend)
  Aura serve --reload          Start API server with auto-reload
  Aura init-db                 Create database extension and tables
  Aura backend test --cov      Run backend tests with coverage

  All settings in Aura config/config/aura.yaml (run_mode, host, port, database_url, ...).
"""


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="Aura",
        description="Aura Swarm — unified launcher. Commands delegate to entries (e.g. backend). Use 'Aura backend <cmd> [args...]' or shortcuts like 'Aura serve', 'Aura init-db'.",
        epilog=_EPILOG.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="store_true", help="Show Aura Swarm launcher version")
    sub = parser.add_subparsers(dest="command", metavar="<command>", help="Command to run")

    # --- One-click: up, dev, down (mode from config run_mode: node | local | docker) ---
    p_up = sub.add_parser("up", help="One-click start (mode from config: node/local = DB+serve, docker = compose up)")
    p_up.set_defaults(func="up")
    p_dev = sub.add_parser("dev", help="One-click dev (same as up with --reload when node/local)")
    p_dev.set_defaults(func="dev")
    p_down = sub.add_parser("down", help="One-click stop (mode from config: docker = compose stop, node/local = pkill backend)")
    p_down.set_defaults(func="down")
    p_configure = sub.add_parser("configure", help="Create config/aura.yaml from example if missing (unified config)")
    p_configure.set_defaults(func="configure")

    # --- Entry: backend (agent-backend) ---
    p_backend = sub.add_parser(
        "backend",
        help="Run agent-backend (serve, init-db, test, start, stop, restart, health, configure, ...)",
        description="Pass a backend subcommand and optional args. Example: Aura backend serve --reload",
    )
    p_backend.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        metavar="args",
        help="Backend subcommand and options (e.g. serve, init-db, test --cov)",
    )
    p_backend.set_defaults(entry="backend")

    # --- Shortcuts (forward to backend) ---
    shortcuts_help = {
        "serve": "Start the API server (backend serve)",
        "init-db": "Create DB extension and tables",
        "test": "Run backend tests (pytest)",
        "reload-config": "POST /admin/reload (hot reload config)",
        "archive": "Run Celery archive task once",
        "health": "GET /health (readiness check)",
        "version": "Print backend version",
        "start": "Docker Compose up -d",
        "stop": "Docker Compose stop",
        "restart": "Docker Compose restart",
        "try-models": "Call configured chat models (test connectivity)",
    }
    for cmd in shortcuts_help:
        h = shortcuts_help[cmd]
        p = sub.add_parser(cmd, help=h)
        p.add_argument("args", nargs=argparse.REMAINDER, metavar="[args...]", help=f"Options for backend {cmd}")
        p.set_defaults(entry="backend", shortcut=cmd)

    args, unknown = parser.parse_known_args()
    if getattr(args, "version", False):
        print(__version__)
        return 0
    if args.command is None:
        parser.print_help()
        return 0

    if getattr(args, "func", None) == "configure":
        aura_root = Path(__file__).resolve().parent.parent
        config_dir = aura_root / "config"
        aura_yaml = config_dir / "aura.yaml"
        example = config_dir / "aura.yaml.example"
        config_dir.mkdir(parents=True, exist_ok=True)
        if not aura_yaml.exists() and example.exists():
            aura_yaml.write_text(example.read_text(), encoding="utf-8")
            print("Created config/aura.yaml. Edit it (run_mode, database_url, port, etc.).")
        elif aura_yaml.exists():
            print("config/aura.yaml already exists.")
        else:
            print("Warning: config/aura.yaml.example not found.", file=sys.stderr)
        return 0

    # One-click up / dev / down (use run_mode from Aura config/aura.yaml)
    if getattr(args, "func", None) == "up":
        run_mode = _get_run_mode()
        if run_mode == "docker":
            _run_backend(["start"])
        else:
            code = _run_run_script(run_mode)
            if code != 0:
                print("Aura up failed (exit code %d). See output above." % code, file=sys.stderr)
            return code
    if getattr(args, "func", None) == "dev":
        run_mode = _get_run_mode()
        if run_mode == "docker":
            _run_backend(["start"])
        else:
            code = _run_run_script(run_mode, env_extra={"DEV": "1"})
            if code != 0:
                print("Aura dev failed (exit code %d). See output above." % code, file=sys.stderr)
            return code
    if getattr(args, "func", None) == "down":
        run_mode = _get_run_mode()
        if run_mode == "docker":
            _run_backend(["stop"])
        else:
            # node/local: stop the backend process (pkill returns 1 if no match)
            subprocess.run(["pkill", "-f", "agent-backend serve"], capture_output=True)
            return 0

    if getattr(args, "entry", None) == "backend":
        shortcut = getattr(args, "shortcut", None)
        remainder = getattr(args, "args", None) or []
        remainder = [a for a in remainder if a != "--"]
        # Pass through any args the main parser didn't recognize (e.g. Aura test -v -> backend test -v)
        remainder = remainder + unknown
        if shortcut:
            argv = [shortcut] + remainder  # e.g. Aura serve --reload -> ['serve', '--reload']
        else:
            argv = remainder               # e.g. Aura backend serve --reload -> ['serve', '--reload']
        _run_backend(argv)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
