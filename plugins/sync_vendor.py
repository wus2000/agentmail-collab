"""Copy the AgentMail core package into each plugin package."""

from __future__ import annotations

import shutil
from pathlib import Path


CORE = Path(__file__).resolve().parents[1]
PLUGIN_ROOTS = [
    CORE / "plugins" / "codex-marketplace" / "plugins" / "agentmail",
    CORE / "plugins" / "claude-marketplace" / "plugins" / "agentmail",
]
CORE_FILES = [
    "__init__.py",
    "__main__.py",
    "cli.py",
    "codex_bridge.py",
    "daemon.py",
    "mcp_server.py",
    "models.py",
    "notify.py",
    "service.py",
    "store.py",
]


def sync_one(plugin_root: Path) -> None:
    target = plugin_root / "vendor" / "agentmail"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in CORE_FILES:
        shutil.copy2(CORE / name, target / name)


def main() -> None:
    for plugin_root in PLUGIN_ROOTS:
        sync_one(plugin_root)
        for script in (plugin_root / "bin").glob("agentmail*"):
            script.chmod(0o755)


if __name__ == "__main__":
    main()
