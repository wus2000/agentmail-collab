"""Copy the AgentMail core package into each plugin package.

Run without arguments to sync the vendored runtime in both plugin payloads.
Run with ``--check`` to verify the vendored copy matches source without
writing; exits non-zero on drift. CI uses ``--check`` to catch contributors
who forget to rerun this script after editing core modules.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
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
OPTIONAL_FILES = ["py.typed"]


def existing_core_files() -> list[str]:
    files = list(CORE_FILES)
    files.extend(name for name in OPTIONAL_FILES if (CORE / name).exists())
    return files


def sync_one(plugin_root: Path) -> None:
    target = plugin_root / "vendor" / "agentmail"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in existing_core_files():
        shutil.copy2(CORE / name, target / name)


def check_one(plugin_root: Path) -> list[str]:
    target = plugin_root / "vendor" / "agentmail"
    drift: list[str] = []
    if not target.exists():
        return [f"{target} missing"]
    expected = set(existing_core_files())
    actual = {p.name for p in target.iterdir() if p.is_file()}
    for missing in sorted(expected - actual):
        drift.append(f"{target / missing} missing")
    for extra in sorted(actual - expected):
        drift.append(f"{target / extra} unexpected")
    for name in sorted(expected & actual):
        if not filecmp.cmp(CORE / name, target / name, shallow=False):
            drift.append(f"{target / name} differs from {CORE / name}")
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify vendored runtime matches source; exit non-zero on drift.",
    )
    args = parser.parse_args(argv)

    if args.check:
        all_drift: list[str] = []
        for plugin_root in PLUGIN_ROOTS:
            all_drift.extend(check_one(plugin_root))
        if all_drift:
            print("Vendored runtime drift detected:", file=sys.stderr)
            for line in all_drift:
                print(f"  {line}", file=sys.stderr)
            print(
                "\nRun `python plugins/sync_vendor.py` and commit the updated vendor tree.",
                file=sys.stderr,
            )
            return 1
        print("Vendored runtime is in sync with source.")
        return 0

    for plugin_root in PLUGIN_ROOTS:
        sync_one(plugin_root)
        for script in (plugin_root / "bin").glob("agentmail*"):
            script.chmod(0o755)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
