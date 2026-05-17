"""Command line interface for AgentMail."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from agentmail.notify import (
    read_channel_config,
    run_message_command,
    send_os_notification,
    start_watcher,
    stop_watcher,
    watcher_status,
    write_channel_config,
)
from agentmail.service import AgentMailError, AgentMailService
from agentmail.store import AgentMailStore, default_db_path


def _parse_json_value(value: str | None, default: Any) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc}") from exc


def _read_body(args: argparse.Namespace) -> str:
    if getattr(args, "body_file", None):
        return Path(args.body_file).expanduser().read_text(encoding="utf-8")
    if getattr(args, "body", None):
        return args.body
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _service(args: argparse.Namespace) -> AgentMailService:
    db_path = args.db or default_db_path(getattr(args, "workspace", None))
    return AgentMailService(AgentMailStore(db_path))


def _workspace_path(workspace: str) -> Path:
    path = Path(workspace).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"workspace does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"workspace is not a directory: {path}")
    return path


def _auto_listen(preferred_port: int = 4500) -> str:
    if _tcp_port_available(preferred_port):
        return f"ws://127.0.0.1:{preferred_port}"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return f"ws://127.0.0.1:{sock.getsockname()[1]}"


def _tcp_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _launcher_listen(args: argparse.Namespace) -> str:
    return args.listen or os.environ.get("AGENTMAIL_CODEX_APP_SERVER") or _auto_listen()


def _agentmail_module_command(args: argparse.Namespace, subcommand: list[str]) -> str:
    parts = [sys.executable, "-m", "agentmail"]
    if args.db:
        parts.extend(["--db", args.db])
    parts.extend(subcommand)
    package_parent = Path(__file__).resolve().parent.parent
    return f"PYTHONPATH={shlex.quote(str(package_parent))}${{PYTHONPATH:+:$PYTHONPATH}} {shlex.join(parts)}"


def _applescript_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _open_terminal(command: str) -> bool:
    if sys.platform != "darwin":
        return False
    script = f'tell application "Terminal" to do script {_applescript_quote(command)}'
    completed = subprocess.run(["osascript", "-e", script], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return completed.returncode == 0


def _emit(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if isinstance(payload, list):
        for item in payload:
            _emit_item(item)
    else:
        _emit_item(payload)


def _emit_item(item: Any) -> None:
    if isinstance(item, dict):
        if "message" in item:
            msg = item["message"]
            print(f"{msg['id']} [{msg['status']}] {msg['from_agent']} -> {', '.join(msg['to_agents'])}: {msg['subject']}")
            return
        if isinstance(item.get("agent"), dict) and isinstance(item.get("room"), dict):
            print(f"joined room={item['room']['name']} agent={item['agent']['name']} ({item['agent']['kind']})")
            return
        if "thread" in item and "messages" in item:
            print(f"# {item['thread']['title']} ({len(item['messages'])} messages)")
            for msg in item["messages"]:
                print(f"- {msg['created_at']} {msg['from_agent']} -> {', '.join(msg['to_agents'])}: {msg['subject']} [{msg['status']}]")
            return
        if "claim" in item:
            claim = item["claim"]
            print(f"{claim['id']} active: {', '.join(claim['paths'])}")
            return
    print(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_join(args: argparse.Namespace) -> Any:
    caps = args.capability or []
    service = _service(args)
    joined = service.join(args.agent, args.kind, args.room, args.workspace, caps)
    if args.kind == "claude":
        joined["channel"] = write_channel_config(service.store.db_path, args.room, args.agent)
    return joined


def cmd_start(args: argparse.Namespace) -> Any:
    service = _service(args)
    caps = args.capability or []
    joined = service.join(args.agent, args.kind, args.room, args.workspace, caps)
    channel = None
    if args.kind == "claude":
        channel = write_channel_config(service.store.db_path, args.room, args.agent)
    return {
        "joined": joined,
        "peers": service.peers(args.room),
        "inbox": service.inbox(
            args.agent,
            args.room,
            include_resolved=False,
            include_seen=True,
            limit=args.limit,
        ),
        "channel": channel,
    }


def cmd_peers(args: argparse.Namespace) -> Any:
    return _service(args).peers(args.room)


def cmd_status(args: argparse.Namespace) -> Any:
    return _service(args).status(args.room, args.agent, args.limit)


def cmd_room_status(args: argparse.Namespace) -> Any:
    return _service(args).set_room_status(args.room, args.status, args.agent)


def cmd_send(args: argparse.Namespace) -> Any:
    return _service(args).send(
        from_agent=args.from_agent,
        to_agents=args.to,
        room_name=args.room,
        thread_title=args.thread,
        subject=args.subject,
        body=_read_body(args),
        refs=_parse_json_value(args.refs, []),
        tags=args.tag or [],
        expects_reply=not args.no_reply,
    )


def cmd_inbox(args: argparse.Namespace) -> Any:
    return _service(args).inbox(
        args.agent,
        args.room,
        include_resolved=args.include_resolved,
        include_seen=not args.unseen_only,
        limit=args.limit,
    )


def cmd_read_thread(args: argparse.Namespace) -> Any:
    return _service(args).read_thread(args.room, args.thread)


def cmd_mark(args: argparse.Namespace) -> Any:
    return _service(args).mark(args.message, args.status, args.agent)


def cmd_reply(args: argparse.Namespace) -> Any:
    return _service(args).reply(
        args.message,
        args.agent,
        _read_body(args),
        refs=_parse_json_value(args.refs, []),
        tags=args.tag or [],
        resolve_original=args.resolve,
    )


def cmd_note(args: argparse.Namespace) -> Any:
    return _service(args).note(
        from_agent=args.agent,
        room_name=args.room,
        thread_title=args.thread,
        body=_read_body(args),
        refs=_parse_json_value(args.refs, []),
        tags=args.tag or [],
    )


def cmd_artifact_add(args: argparse.Namespace) -> Any:
    return _service(args).add_artifact(
        args.room,
        args.thread,
        args.agent,
        args.type,
        args.path,
        args.summary,
    )


def cmd_artifacts(args: argparse.Namespace) -> Any:
    return _service(args).artifacts(args.room, args.thread, args.limit)


def cmd_claim_scope(args: argparse.Namespace) -> Any:
    return _service(args).claim_scope(
        args.agent,
        args.room,
        args.path,
        args.reason,
        ttl_seconds=args.ttl,
        force=args.force,
    )


def cmd_release_scope(args: argparse.Namespace) -> Any:
    return _service(args).release_scope(args.agent, args.room, args.path)


def cmd_timeline(args: argparse.Namespace) -> Any:
    return _service(args).timeline(args.room, args.limit)


def cmd_watch(args: argparse.Namespace) -> Any:
    service = _service(args)
    seen: set[str] = set()
    if args.since_now:
        seen.update(
            message["id"]
            for message in service.inbox(args.agent, args.room, include_resolved=False, include_seen=True, limit=args.limit)
        )
    deadline = time.time() + args.seconds if args.seconds else None
    while True:
        messages = service.inbox(args.agent, args.room, include_resolved=False, include_seen=True, limit=args.limit)
        fresh = [message for message in reversed(messages) if message["id"] not in seen]
        for message in fresh:
            seen.add(message["id"])
            line = f"{message['id']} {message['from_agent']} -> {', '.join(message['to_agents'])}: {message['subject']}"
            if args.include_body:
                line += f"\n{message['body']}"
            print(line, flush=True)
            if args.notify:
                send_os_notification(
                    f"AgentMail: {args.room}",
                    f"{message['from_agent']}: {message['subject']}",
                )
            if args.command:
                rc = run_message_command(message, args.command, args.command_timeout)
                print(f"command exit={rc} message={message['id']}", flush=True)
        if args.once:
            return {"seen": len(seen)}
        if deadline and time.time() >= deadline:
            return {"seen": len(seen)}
        time.sleep(args.interval)


def cmd_notify_start(args: argparse.Namespace) -> Any:
    db_path = _service(args).store.db_path
    return start_watcher(
        db_path,
        args.room,
        args.agent,
        interval=args.interval,
        notify=args.os_notify and not args.no_notify,
        command=args.command or "",
        since_now=not args.include_existing,
    )


def cmd_notify_stop(args: argparse.Namespace) -> Any:
    db_path = _service(args).store.db_path
    return stop_watcher(db_path, args.room, args.agent)


def cmd_notify_status(args: argparse.Namespace) -> Any:
    db_path = _service(args).store.db_path
    return watcher_status(db_path, args.room, args.agent)


def cmd_channel_status(args: argparse.Namespace) -> Any:
    db_path = _service(args).store.db_path
    return {
        "db_path": str(db_path),
        "channel": read_channel_config(db_path),
    }


def cmd_channel_config(args: argparse.Namespace) -> Any:
    db_path = _service(args).store.db_path
    return write_channel_config(db_path, args.room, args.agent, enabled=not args.disable)


def cmd_codex_bridge_start(args: argparse.Namespace) -> Any:
    from agentmail.codex_bridge import start_bridge

    db_path = _service(args).store.db_path
    return start_bridge(
        db_path,
        args.room,
        args.agent,
        workspace=args.workspace,
        listen=args.listen,
        thread_id=args.thread_id,
        mode=args.mode,
        interval=args.interval,
        since_now=not args.include_existing,
        start_app_server=not args.no_app_server,
    )


def cmd_codex_bridge_watch(args: argparse.Namespace) -> Any:
    from agentmail.codex_bridge import run_bridge_loop

    db_path = _service(args).store.db_path
    return run_bridge_loop(
        db_path,
        args.room,
        args.agent,
        workspace=args.workspace,
        listen=args.listen,
        thread_id=args.thread_id,
        mode=args.mode,
        interval=args.interval,
        since_now=args.since_now,
        once=args.once,
    )


def cmd_codex_bridge_stop(args: argparse.Namespace) -> Any:
    from agentmail.codex_bridge import stop_bridge

    db_path = _service(args).store.db_path
    return stop_bridge(db_path, args.room, args.agent)


def cmd_codex_bridge_status(args: argparse.Namespace) -> Any:
    from agentmail.codex_bridge import bridge_status

    db_path = _service(args).store.db_path
    return bridge_status(db_path, args.room, args.agent)


def cmd_codex_bridge_run(args: argparse.Namespace) -> Any:
    from agentmail.codex_bridge import clear_foreground_run, register_foreground_run, start_bridge, stop_bridge

    db_path = _service(args).store.db_path
    start_bridge(
        db_path,
        args.room,
        args.agent,
        workspace=args.workspace,
        listen=args.listen,
        thread_id=args.thread_id,
        mode=args.mode,
        interval=args.interval,
        since_now=not args.include_existing,
        start_app_server=True,
    )
    cmd = ["codex", "--remote", args.listen]
    if args.workspace:
        cmd.extend(["--cd", args.workspace])
    register_foreground_run(db_path, args.room, args.agent)
    try:
        process = subprocess.Popen(cmd)
        register_foreground_run(db_path, args.room, args.agent, remote_pid=process.pid)
        return {"codex_exit_code": process.wait()}
    finally:
        clear_foreground_run(db_path, args.room, args.agent)
        if not args.keep_running:
            stop_bridge(db_path, args.room, args.agent)


def cmd_launch_codex(args: argparse.Namespace) -> Any:
    workspace = _workspace_path(args.workspace)
    listen = _launcher_listen(args)
    service = _service(args)
    joined = service.join(
        args.agent,
        "codex",
        args.room,
        str(workspace),
        ["peer-mailbox", "code-collaboration", "active-wakeup"],
    )
    run_args = argparse.Namespace(
        **{
            **vars(args),
            "workspace": str(workspace),
            "listen": listen,
            "no_app_server": False,
        }
    )
    result = cmd_codex_bridge_run(run_args)
    return {"joined": joined, "listen": listen, **result}


def cmd_bootstrap_codex(args: argparse.Namespace) -> Any:
    workspace = _workspace_path(args.workspace)
    listen = _launcher_listen(args)
    service = _service(args)
    joined = service.join(
        args.agent,
        "codex",
        args.room,
        str(workspace),
        ["peer-mailbox", "code-collaboration", "active-wakeup"],
    )
    launch_command = _agentmail_module_command(
        args,
        [
            "launch-codex",
            "--agent",
            args.agent,
            "--room",
            args.room,
            "--workspace",
            str(workspace),
            "--listen",
            listen,
            "--interval",
            str(args.interval),
            "--mode",
            args.mode,
        ],
    )
    if args.thread_id:
        launch_command += " " + shlex.join(["--thread-id", args.thread_id])
    if args.include_existing:
        launch_command += " --include-existing"
    if args.keep_running:
        launch_command += " --keep-running"
    command = f"cd {shlex.quote(str(workspace))} && {launch_command}"
    opened = False if args.dry_run else (_open_terminal(command) if args.open_terminal else False)
    return {
        "joined": joined,
        "workspace": str(workspace),
        "db_path": str(service.store.db_path),
        "listen": listen,
        "opened_terminal": opened,
        "command": command,
        "next_steps": [
            "Use the newly opened Codex Remote TUI for AgentMail-aware collaboration." if opened else "Run the command shown above in a terminal to start the AgentMail-aware Codex Remote TUI.",
            f"In Claude Code, start or reload AgentMail and join room `{args.room}` as `claude`.",
        ],
    }


def cmd_doctor(args: argparse.Namespace) -> Any:
    from agentmail.codex_bridge import bridge_status

    workspace = Path(args.workspace).expanduser().resolve()
    service = _service(args)
    db_path = service.store.db_path
    peers = service.peers(args.room)
    channel = read_channel_config(db_path)
    bridge = bridge_status(db_path, args.room, "codex")
    checks = [
        {"name": "workspace_exists", "ok": workspace.exists() and workspace.is_dir(), "detail": str(workspace)},
        {"name": "database_exists", "ok": db_path.exists(), "detail": str(db_path)},
        {"name": "codex_cli", "ok": shutil.which("codex") is not None, "detail": shutil.which("codex") or ""},
        {"name": "claude_cli", "ok": shutil.which("claude") is not None, "detail": shutil.which("claude") or ""},
        {
            "name": "claude_channel_configured",
            "ok": bool(channel and channel.get("enabled") and channel.get("room_name") == args.room),
            "detail": channel or {},
        },
        {
            "name": "codex_bridge_running",
            "ok": bool(bridge.get("running") and bridge.get("app_server_running")),
            "detail": bridge,
        },
    ]
    return {
        "workspace": str(workspace),
        "db_path": str(db_path),
        "room": args.room,
        "peers": peers,
        "checks": checks,
        "ok": all(check["ok"] for check in checks[:4]),
    }


def cmd_serve(args: argparse.Namespace) -> Any:
    from agentmail.daemon import run_server

    run_server(args.host, args.port, args.db)
    return None


def cmd_mcp(args: argparse.Namespace) -> Any:
    from agentmail.mcp_server import run_stdio_server

    run_stdio_server(args.db)
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AgentMail local peer mailbox for coding agents.")
    parser.add_argument("--db", default=os.environ.get("AGENTMAIL_DB"), help="SQLite database path. Defaults to .agentmail/agentmail.db.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    sub = parser.add_subparsers(dest="command", required=True)

    join = sub.add_parser("join", help="Register or refresh an agent in a room.")
    join.add_argument("--agent", required=True)
    join.add_argument("--kind", required=True, choices=["claude", "codex", "other"])
    join.add_argument("--room", default="default")
    join.add_argument("--workspace", default=".")
    join.add_argument("--capability", action="append", default=[])
    join.set_defaults(func=cmd_join)

    start = sub.add_parser("start", help="Join a room and show current peers and inbox.")
    start.add_argument("--agent", required=True)
    start.add_argument("--kind", required=True, choices=["claude", "codex", "other"])
    start.add_argument("--room", default="default")
    start.add_argument("--workspace", default=".")
    start.add_argument("--capability", action="append", default=[])
    start.add_argument("--limit", type=int, default=20)
    start.set_defaults(func=cmd_start)

    peers = sub.add_parser("peers", help="List agents in a room.")
    peers.add_argument("--room", default="default")
    peers.set_defaults(func=cmd_peers)

    status = sub.add_parser("status", help="Show room, peers, inbox, active claims, and DB path.")
    status.add_argument("--agent")
    status.add_argument("--room", default="default")
    status.add_argument("--limit", type=int, default=20)
    status.set_defaults(func=cmd_status)

    room_status = sub.add_parser("room-status", help="Set a room status: open, paused, or closed.")
    room_status.add_argument("--agent", required=True)
    room_status.add_argument("--room", default="default")
    room_status.add_argument("--status", required=True, choices=["open", "paused", "closed"])
    room_status.set_defaults(func=cmd_room_status)

    send = sub.add_parser("send", help="Send a message.")
    send.add_argument("--from", dest="from_agent", required=True)
    send.add_argument("--to", action="append", required=True)
    send.add_argument("--room", default="default")
    send.add_argument("--thread", default="main")
    send.add_argument("--subject", default="")
    send.add_argument("--body", default="")
    send.add_argument("--body-file")
    send.add_argument("--refs", help="JSON array of refs/artifacts.")
    send.add_argument("--tag", action="append", default=[])
    send.add_argument("--no-reply", action="store_true")
    send.set_defaults(func=cmd_send)

    inbox = sub.add_parser("inbox", help="List inbox messages for an agent.")
    inbox.add_argument("--agent", required=True)
    inbox.add_argument("--room", default="default")
    inbox.add_argument("--include-resolved", action="store_true")
    inbox.add_argument("--unseen-only", action="store_true")
    inbox.add_argument("--limit", type=int, default=50)
    inbox.set_defaults(func=cmd_inbox)

    read_thread = sub.add_parser("read-thread", help="Read all messages in a thread.")
    read_thread.add_argument("--room", default="default")
    read_thread.add_argument("--thread", default="main")
    read_thread.set_defaults(func=cmd_read_thread)

    mark = sub.add_parser("mark", help="Change message status.")
    mark.add_argument("--agent", required=True)
    mark.add_argument("--message", required=True)
    mark.add_argument("--status", required=True)
    mark.set_defaults(func=cmd_mark)

    reply = sub.add_parser("reply", help="Reply to a message.")
    reply.add_argument("--agent", required=True)
    reply.add_argument("--message", required=True)
    reply.add_argument("--body", default="")
    reply.add_argument("--body-file")
    reply.add_argument("--refs")
    reply.add_argument("--tag", action="append", default=[])
    reply.add_argument("--resolve", action="store_true")
    reply.set_defaults(func=cmd_reply)

    note = sub.add_parser("note", help="Write a shared note to a thread.")
    note.add_argument("--agent", required=True)
    note.add_argument("--room", default="default")
    note.add_argument("--thread", default="main")
    note.add_argument("--body", default="")
    note.add_argument("--body-file")
    note.add_argument("--refs")
    note.add_argument("--tag", action="append", default=[])
    note.set_defaults(func=cmd_note)

    artifact_add = sub.add_parser("artifact-add", help="Register an artifact path in a thread.")
    artifact_add.add_argument("--agent", required=True)
    artifact_add.add_argument("--room", default="default")
    artifact_add.add_argument("--thread", default="main")
    artifact_add.add_argument("--type", default="file")
    artifact_add.add_argument("--path", required=True)
    artifact_add.add_argument("--summary", default="")
    artifact_add.set_defaults(func=cmd_artifact_add)

    artifacts = sub.add_parser("artifacts", help="List artifacts for a room or thread.")
    artifacts.add_argument("--room", default="default")
    artifacts.add_argument("--thread")
    artifacts.add_argument("--limit", type=int, default=50)
    artifacts.set_defaults(func=cmd_artifacts)

    claim = sub.add_parser("claim-scope", help="Claim file/path scope to reduce accidental double writes.")
    claim.add_argument("--agent", required=True)
    claim.add_argument("--room", default="default")
    claim.add_argument("--path", action="append", required=True)
    claim.add_argument("--reason", default="")
    claim.add_argument("--ttl", type=int, default=3600)
    claim.add_argument("--force", action="store_true")
    claim.set_defaults(func=cmd_claim_scope)

    release = sub.add_parser("release-scope", help="Release active path claims.")
    release.add_argument("--agent", required=True)
    release.add_argument("--room", default="default")
    release.add_argument("--path", action="append", default=[])
    release.set_defaults(func=cmd_release_scope)

    timeline = sub.add_parser("timeline", help="Show recent events for a room.")
    timeline.add_argument("--room", default="default")
    timeline.add_argument("--limit", type=int, default=50)
    timeline.set_defaults(func=cmd_timeline)

    watch = sub.add_parser("watch", help="Poll inbox and print new notifications.")
    watch.add_argument("--agent", required=True)
    watch.add_argument("--room", default="default")
    watch.add_argument("--limit", type=int, default=50)
    watch.add_argument("--interval", type=float, default=2.0)
    watch.add_argument("--seconds", type=float, default=0)
    watch.add_argument("--once", action="store_true")
    watch.add_argument("--since-now", action="store_true", help="Ignore messages already present when the watcher starts.")
    watch.add_argument("--notify", action="store_true", help="Show an OS notification for each new message.")
    watch.add_argument("--include-body", action="store_true", help="Print message body after the notification line.")
    watch.add_argument("--command", help="Shell command to run for each new message. Message JSON is passed on stdin.")
    watch.add_argument("--command-timeout", type=float, default=30.0)
    watch.set_defaults(func=cmd_watch)

    notify_start = sub.add_parser("notify-start", help="Start a background inbox watcher for an agent.")
    notify_start.add_argument("--agent", required=True)
    notify_start.add_argument("--room", default="default")
    notify_start.add_argument("--workspace", default=".")
    notify_start.add_argument("--interval", type=float, default=2.0)
    notify_start.add_argument("--os-notify", action="store_true", help="Show OS notifications for new messages.")
    notify_start.add_argument("--no-notify", action="store_true", help=argparse.SUPPRESS)
    notify_start.add_argument("--include-existing", action="store_true", help="Notify messages already in the inbox.")
    notify_start.add_argument("--command", help="Shell command to run for each new message. Message JSON is passed on stdin.")
    notify_start.set_defaults(func=cmd_notify_start)

    notify_stop = sub.add_parser("notify-stop", help="Stop a background inbox watcher for an agent.")
    notify_stop.add_argument("--agent", required=True)
    notify_stop.add_argument("--room", default="default")
    notify_stop.add_argument("--workspace", default=".")
    notify_stop.set_defaults(func=cmd_notify_stop)

    notify_status = sub.add_parser("notify-status", help="Show background watcher status for an agent.")
    notify_status.add_argument("--agent", required=True)
    notify_status.add_argument("--room", default="default")
    notify_status.add_argument("--workspace", default=".")
    notify_status.set_defaults(func=cmd_notify_status)

    channel_config = sub.add_parser("channel-config", help="Configure the Claude channel target room and agent.")
    channel_config.add_argument("--agent", required=True)
    channel_config.add_argument("--room", default="default")
    channel_config.add_argument("--workspace", default=".")
    channel_config.add_argument("--disable", action="store_true")
    channel_config.set_defaults(func=cmd_channel_config)

    channel_status = sub.add_parser("channel-status", help="Show Claude channel configuration.")
    channel_status.add_argument("--workspace", default=".")
    channel_status.set_defaults(func=cmd_channel_status)

    launch_codex = sub.add_parser(
        "launch-codex",
        help="Join AgentMail and run an AgentMail-aware Codex Remote TUI.",
    )
    _add_codex_launcher_args(launch_codex)
    launch_codex.add_argument("--keep-running", action="store_true", help="Leave the bridge and managed app-server running when Codex exits.")
    launch_codex.set_defaults(func=cmd_launch_codex)

    bootstrap_codex = sub.add_parser(
        "bootstrap-codex",
        help="Prepare the current workspace and open an AgentMail-aware Codex Remote TUI.",
    )
    _add_codex_launcher_args(bootstrap_codex)
    bootstrap_codex.add_argument("--open-terminal", action=argparse.BooleanOptionalAction, default=True)
    bootstrap_codex.add_argument("--keep-running", action="store_true", help="Leave the bridge and managed app-server running when Codex exits.")
    bootstrap_codex.add_argument("--dry-run", action="store_true", help="Print the launch command without opening a terminal.")
    bootstrap_codex.set_defaults(func=cmd_bootstrap_codex)

    doctor = sub.add_parser("doctor", help="Check local AgentMail collaboration state for a workspace.")
    doctor.add_argument("--room", default="default")
    doctor.add_argument("--workspace", default=".")
    doctor.set_defaults(func=cmd_doctor)

    codex_bridge = sub.add_parser("codex-bridge", help="Experimental Codex App Server bridge.")
    codex_bridge_sub = codex_bridge.add_subparsers(dest="codex_bridge_command", required=True)

    codex_bridge_start = codex_bridge_sub.add_parser(
        "start",
        help="Start a background bridge that delivers AgentMail inbox messages into Codex App Server.",
    )
    _add_codex_bridge_common_args(codex_bridge_start)
    codex_bridge_start.add_argument("--interval", type=float, default=2.0)
    codex_bridge_start.add_argument("--include-existing", action="store_true")
    codex_bridge_start.add_argument("--no-app-server", action="store_true", help="Do not start codex app-server; connect to an existing endpoint.")
    codex_bridge_start.set_defaults(func=cmd_codex_bridge_start)

    codex_bridge_watch = codex_bridge_sub.add_parser("watch", help="Run the bridge loop in the foreground.")
    _add_codex_bridge_common_args(codex_bridge_watch)
    codex_bridge_watch.add_argument("--interval", type=float, default=2.0)
    codex_bridge_watch.add_argument("--since-now", action="store_true")
    codex_bridge_watch.add_argument("--once", action="store_true")
    codex_bridge_watch.set_defaults(func=cmd_codex_bridge_watch)

    codex_bridge_stop = codex_bridge_sub.add_parser("stop", help="Stop the background Codex bridge.")
    codex_bridge_stop.add_argument("--agent", default="codex")
    codex_bridge_stop.add_argument("--room", default="default")
    codex_bridge_stop.add_argument("--workspace", default=".")
    codex_bridge_stop.set_defaults(func=cmd_codex_bridge_stop)

    codex_bridge_status = codex_bridge_sub.add_parser("status", help="Show Codex bridge status.")
    codex_bridge_status.add_argument("--agent", default="codex")
    codex_bridge_status.add_argument("--room", default="default")
    codex_bridge_status.add_argument("--workspace", default=".")
    codex_bridge_status.set_defaults(func=cmd_codex_bridge_status)

    codex_bridge_run = codex_bridge_sub.add_parser(
        "run",
        help="Start managed app-server + bridge, then run `codex --remote` in the foreground.",
    )
    _add_codex_bridge_common_args(codex_bridge_run)
    codex_bridge_run.add_argument("--interval", type=float, default=2.0)
    codex_bridge_run.add_argument("--include-existing", action="store_true")
    codex_bridge_run.add_argument("--keep-running", action="store_true", help="Leave the bridge and managed app-server running when Codex exits.")
    codex_bridge_run.set_defaults(func=cmd_codex_bridge_run)

    serve = sub.add_parser("serve", help="Run local JSON RPC daemon.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=cmd_serve)

    mcp = sub.add_parser("mcp", help="Run stdio MCP server.")
    mcp.set_defaults(func=cmd_mcp)
    return parser


def _add_codex_bridge_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent", default="codex")
    parser.add_argument("--room", default="default")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--listen", default=os.environ.get("AGENTMAIL_CODEX_APP_SERVER", "ws://127.0.0.1:4500"))
    parser.add_argument("--thread-id", default="", help="Codex App Server thread id. If omitted, one loaded thread is auto-selected.")
    parser.add_argument("--mode", default="turn-start", choices=["turn-start", "inject"])


def _add_codex_launcher_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent", default="codex")
    parser.add_argument("--room", default="default")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--listen", default="", help="Codex App Server websocket URL. Defaults to an available localhost port.")
    parser.add_argument("--thread-id", default="", help="Codex App Server thread id. If omitted, one loaded thread is auto-selected.")
    parser.add_argument("--mode", default="turn-start", choices=["turn-start", "inject"])
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--include-existing", action="store_true")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
        if result is not None:
            _emit(result, args.json)
        return 0
    except (AgentMailError, OSError, ValueError) as exc:
        print(f"agentmail: error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        if exc.__class__.__name__ == "CodexBridgeError":
            print(f"agentmail: error: {exc}", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
