"""Notification and watcher helpers for AgentMail."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any
from datetime import datetime


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "default"


def watch_paths(db_path: str | os.PathLike[str], room_name: str, agent_name: str) -> dict[str, Path]:
    db = Path(db_path).expanduser()
    watch_dir = db.parent / "watch"
    log_dir = db.parent / "logs"
    stem = f"{safe_name(room_name)}-{safe_name(agent_name)}"
    return {
        "watch_dir": watch_dir,
        "log_dir": log_dir,
        "pid": watch_dir / f"{stem}.pid",
        "log": log_dir / f"{stem}.log",
    }


def channel_config_path(db_path: str | os.PathLike[str]) -> Path:
    return Path(db_path).expanduser().parent / "channel.json"


def read_channel_config(db_path: str | os.PathLike[str]) -> dict[str, Any] | None:
    path = channel_config_path(db_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def write_channel_config(
    db_path: str | os.PathLike[str],
    room_name: str,
    agent_name: str,
    enabled: bool = True,
) -> dict[str, Any]:
    path = channel_config_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled": enabled,
        "room_name": room_name,
        "agent_name": agent_name,
        "updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"config": payload, "config_file": str(path)}


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def watcher_status(db_path: str | os.PathLike[str], room_name: str, agent_name: str) -> dict[str, Any]:
    paths = watch_paths(db_path, room_name, agent_name)
    pid = _read_pid(paths["pid"])
    running = bool(pid and pid_alive(pid))
    return {
        "agent": agent_name,
        "room": room_name,
        "running": running,
        "pid": pid,
        "pid_file": str(paths["pid"]),
        "log_file": str(paths["log"]),
    }


def start_watcher(
    db_path: str | os.PathLike[str],
    room_name: str,
    agent_name: str,
    interval: float = 2.0,
    notify: bool = False,
    command: str = "",
    since_now: bool = True,
) -> dict[str, Any]:
    paths = watch_paths(db_path, room_name, agent_name)
    paths["watch_dir"].mkdir(parents=True, exist_ok=True)
    paths["log_dir"].mkdir(parents=True, exist_ok=True)
    existing = watcher_status(db_path, room_name, agent_name)
    if existing["running"]:
        return {**existing, "started": False}

    cmd = [
        sys.executable,
        "-m",
        "agentmail",
        "--db",
        str(Path(db_path).expanduser()),
        "--json",
        "watch",
        "--agent",
        agent_name,
        "--room",
        room_name,
        "--interval",
        str(interval),
    ]
    if since_now:
        cmd.append("--since-now")
    if notify:
        cmd.append("--notify")
    if command:
        cmd.extend(["--command", command])

    log = paths["log"].open("a", encoding="utf-8")
    process = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    log.close()
    pid = process.pid
    # This process is intentionally detached and tracked by pid file.
    process._child_created = False  # type: ignore[attr-defined]
    paths["pid"].write_text(str(process.pid), encoding="utf-8")
    return {
        "agent": agent_name,
        "room": room_name,
        "running": True,
        "started": True,
        "pid": pid,
        "pid_file": str(paths["pid"]),
        "log_file": str(paths["log"]),
    }


def stop_watcher(db_path: str | os.PathLike[str], room_name: str, agent_name: str) -> dict[str, Any]:
    paths = watch_paths(db_path, room_name, agent_name)
    pid = _read_pid(paths["pid"])
    stopped = False
    if pid and pid_alive(pid):
        os.kill(pid, signal.SIGTERM)
        stopped = True
    try:
        paths["pid"].unlink()
    except FileNotFoundError:
        pass
    return {
        "agent": agent_name,
        "room": room_name,
        "stopped": stopped,
        "pid": pid,
        "pid_file": str(paths["pid"]),
        "log_file": str(paths["log"]),
    }


def send_os_notification(title: str, message: str) -> bool:
    if sys.platform == "darwin":
        script = f'display notification "{_applescript_escape(message)}" with title "{_applescript_escape(title)}"'
        return _run_quiet(["osascript", "-e", script])
    return False


def run_message_command(message: dict[str, Any], command: str, timeout: float = 30.0) -> int:
    env = os.environ.copy()
    env.update(
        {
            "AGENTMAIL_MESSAGE_ID": message.get("id", ""),
            "AGENTMAIL_FROM": message.get("from_agent", ""),
            "AGENTMAIL_SUBJECT": message.get("subject", ""),
            "AGENTMAIL_TRACE_ID": message.get("trace_id", ""),
            "AGENTMAIL_THREAD_ID": message.get("thread_id", ""),
        }
    )
    completed = subprocess.run(
        command,
        input=json.dumps(message, ensure_ascii=False),
        text=True,
        shell=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    return completed.returncode


def _run_quiet(cmd: list[str]) -> bool:
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return True


def _applescript_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
