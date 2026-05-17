"""Minimal stdio MCP server for AgentMail tools.

The implementation intentionally uses only the standard library so AgentMail can
run in a fresh local checkout. It supports the JSON-RPC methods most MCP clients
need for tool discovery and tool calls.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime
from typing import Any, Callable

from agentmail.daemon import call_method
from agentmail.notify import read_channel_config, write_channel_config
from agentmail.service import AgentMailService
from agentmail.store import AgentMailStore
from agentmail.store import default_db_path


_CHANNEL_PROCESS_STARTED_AT = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
    }


TOOLS = [
    _tool(
        "agentmail_join",
        "Register this agent in a room and refresh its heartbeat.",
        {
            "agent_name": {"type": "string"},
            "agent_kind": {"type": "string", "enum": ["claude", "codex", "other"]},
            "room_name": {"type": "string", "default": "default"},
            "workspace": {"type": "string", "default": "."},
            "capabilities": {"type": "array", "items": {"type": "string"}},
        },
        ["agent_name", "agent_kind"],
    ),
    _tool("agentmail_peers", "List agents in a room.", {"room_name": {"type": "string", "default": "default"}}),
    _tool(
        "agentmail_status",
        "Show room, peers, inbox, active claims, and DB path.",
        {
            "room_name": {"type": "string", "default": "default"},
            "agent_name": {"type": "string"},
            "limit": {"type": "integer", "default": 20},
        },
    ),
    _tool(
        "agentmail_set_room_status",
        "Pause, reopen, or close a room.",
        {
            "room_name": {"type": "string", "default": "default"},
            "status": {"type": "string", "enum": ["open", "paused", "closed"]},
            "actor": {"type": "string"},
        },
        ["status", "actor"],
    ),
    _tool(
        "agentmail_send",
        "Send a natural-language message to one or more peer agents.",
        {
            "from_agent": {"type": "string"},
            "to_agents": {"type": "array", "items": {"type": "string"}},
            "room_name": {"type": "string", "default": "default"},
            "thread_title": {"type": "string", "default": "main"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "refs": {"type": "array", "items": {"type": "object"}},
            "tags": {"type": "array", "items": {"type": "string"}},
            "expects_reply": {"type": "boolean", "default": True},
        },
        ["from_agent", "to_agents", "body"],
    ),
    _tool(
        "agentmail_inbox",
        "List messages addressed to an agent.",
        {
            "agent_name": {"type": "string"},
            "room_name": {"type": "string", "default": "default"},
            "include_resolved": {"type": "boolean", "default": False},
            "include_seen": {"type": "boolean", "default": True},
            "limit": {"type": "integer", "default": 50},
        },
        ["agent_name"],
    ),
    _tool(
        "agentmail_read_thread",
        "Read a room thread with all messages in chronological order.",
        {"room_name": {"type": "string", "default": "default"}, "thread": {"type": "string", "default": "main"}},
    ),
    _tool(
        "agentmail_mark",
        "Mark a message status, such as seen, claimed, resolved, or cancelled.",
        {"message_id": {"type": "string"}, "status": {"type": "string"}, "actor": {"type": "string"}},
        ["message_id", "status", "actor"],
    ),
    _tool(
        "agentmail_reply",
        "Reply to a message in the same thread.",
        {
            "message_id": {"type": "string"},
            "from_agent": {"type": "string"},
            "body": {"type": "string"},
            "refs": {"type": "array", "items": {"type": "object"}},
            "tags": {"type": "array", "items": {"type": "string"}},
            "resolve_original": {"type": "boolean", "default": False},
        },
        ["message_id", "from_agent", "body"],
    ),
    _tool(
        "agentmail_note",
        "Write a shared room note visible to peers.",
        {
            "from_agent": {"type": "string"},
            "room_name": {"type": "string", "default": "default"},
            "thread_title": {"type": "string", "default": "main"},
            "body": {"type": "string"},
            "refs": {"type": "array", "items": {"type": "object"}},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        ["from_agent", "body"],
    ),
    _tool(
        "agentmail_claim_scope",
        "Claim file/path scope before editing to reduce accidental double writes.",
        {
            "agent_name": {"type": "string"},
            "room_name": {"type": "string", "default": "default"},
            "paths": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"},
            "ttl_seconds": {"type": "integer", "default": 3600},
            "force": {"type": "boolean", "default": False},
        },
        ["agent_name", "paths"],
    ),
    _tool(
        "agentmail_add_artifact",
        "Register a file, diff, log, screenshot, or note artifact path in a thread.",
        {
            "room_name": {"type": "string", "default": "default"},
            "thread_title": {"type": "string", "default": "main"},
            "created_by": {"type": "string"},
            "artifact_type": {"type": "string", "default": "file"},
            "path": {"type": "string"},
            "summary": {"type": "string"},
        },
        ["created_by", "path"],
    ),
    _tool(
        "agentmail_artifacts",
        "List registered artifacts for a room or thread.",
        {
            "room_name": {"type": "string", "default": "default"},
            "thread": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
    ),
    _tool(
        "agentmail_release_scope",
        "Release active path claims.",
        {
            "agent_name": {"type": "string"},
            "room_name": {"type": "string", "default": "default"},
            "paths": {"type": "array", "items": {"type": "string"}},
        },
        ["agent_name"],
    ),
    _tool(
        "agentmail_notify_start",
        "Start a background inbox watcher for logs or a command callback. OS notifications are opt-in.",
        {
            "agent_name": {"type": "string"},
            "room_name": {"type": "string", "default": "default"},
            "workspace": {"type": "string"},
            "interval": {"type": "number", "default": 2.0},
            "notify": {"type": "boolean", "default": False},
            "command": {"type": "string"},
            "since_now": {"type": "boolean", "default": True},
        },
        ["agent_name"],
    ),
    _tool(
        "agentmail_notify_stop",
        "Stop a background inbox watcher.",
        {
            "agent_name": {"type": "string"},
            "room_name": {"type": "string", "default": "default"},
            "workspace": {"type": "string"},
        },
        ["agent_name"],
    ),
    _tool(
        "agentmail_notify_status",
        "Show background inbox watcher status.",
        {
            "agent_name": {"type": "string"},
            "room_name": {"type": "string", "default": "default"},
            "workspace": {"type": "string"},
        },
        ["agent_name"],
    ),
    _tool(
        "agentmail_codex_bridge_start",
        "Start the experimental Codex App Server bridge for active Claude-to-Codex delivery.",
        {
            "agent_name": {"type": "string", "default": "codex"},
            "room_name": {"type": "string", "default": "default"},
            "workspace": {"type": "string"},
            "listen": {"type": "string", "default": "ws://127.0.0.1:4500"},
            "thread_id": {"type": "string"},
            "mode": {"type": "string", "enum": ["turn-start", "inject"], "default": "turn-start"},
            "interval": {"type": "number", "default": 2.0},
            "since_now": {"type": "boolean", "default": True},
            "start_app_server": {"type": "boolean", "default": True},
        },
    ),
    _tool(
        "agentmail_codex_bridge_stop",
        "Stop the experimental Codex App Server bridge.",
        {
            "agent_name": {"type": "string", "default": "codex"},
            "room_name": {"type": "string", "default": "default"},
            "workspace": {"type": "string"},
        },
    ),
    _tool(
        "agentmail_codex_bridge_status",
        "Show experimental Codex App Server bridge status.",
        {
            "agent_name": {"type": "string", "default": "codex"},
            "room_name": {"type": "string", "default": "default"},
            "workspace": {"type": "string"},
        },
    ),
    _tool(
        "agentmail_timeline",
        "Show recent room events for audit and recovery.",
        {"room_name": {"type": "string", "default": "default"}, "limit": {"type": "integer", "default": 50}},
    ),
]


TOOL_TO_METHOD = {
    "agentmail_join": "join",
    "agentmail_peers": "peers",
    "agentmail_status": "status",
    "agentmail_set_room_status": "set_room_status",
    "agentmail_send": "send",
    "agentmail_inbox": "inbox",
    "agentmail_read_thread": "read_thread",
    "agentmail_mark": "mark",
    "agentmail_reply": "reply",
    "agentmail_note": "note",
    "agentmail_add_artifact": "add_artifact",
    "agentmail_artifacts": "artifacts",
    "agentmail_claim_scope": "claim_scope",
    "agentmail_release_scope": "release_scope",
    "agentmail_notify_start": "notify_start",
    "agentmail_notify_stop": "notify_stop",
    "agentmail_notify_status": "notify_status",
    "agentmail_codex_bridge_start": "codex_bridge_start",
    "agentmail_codex_bridge_stop": "codex_bridge_stop",
    "agentmail_codex_bridge_status": "codex_bridge_status",
    "agentmail_timeline": "timeline",
}


class AgentMailMCP:
    def __init__(
        self,
        db_path: str | None = None,
        *,
        channel_enabled: bool | None = None,
        output: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.db_path = db_path
        self.active_db_path = db_path
        self.channel_enabled = (
            channel_enabled
            if channel_enabled is not None
            else _truthy(os.environ.get("AGENTMAIL_CHANNEL", "0"))
        )
        self._output = output
        self._channel_stop = threading.Event()
        self._channel_thread: threading.Thread | None = None
        self._channel_seen: set[str] = set()
        self._channel_key: tuple[str, str, str, str] | None = None

    def _db_path_for_call(self, arguments: dict[str, Any]) -> str | None:
        if self.db_path:
            return self.db_path
        workspace = arguments.get("workspace")
        if workspace:
            self.active_db_path = str(default_db_path(workspace))
            return self.active_db_path
        if self.active_db_path:
            return self.active_db_path
        self.active_db_path = str(default_db_path())
        return self.active_db_path

    def _start_channel_thread(self) -> None:
        if not self.channel_enabled or self._output is None:
            return
        if self._channel_thread and self._channel_thread.is_alive():
            return
        self._channel_thread = threading.Thread(target=self._channel_loop, name="agentmail-channel", daemon=True)
        self._channel_thread.start()

    def _channel_loop(self) -> None:
        interval = _float_env("AGENTMAIL_CHANNEL_INTERVAL", 1.0)
        while not self._channel_stop.wait(interval):
            try:
                self._poll_channel_once()
            except Exception as exc:  # pragma: no cover - best-effort background delivery
                print(f"agentmail channel poll error: {exc}", file=sys.stderr, flush=True)

    def _poll_channel_once(self) -> None:
        db_path = self.active_db_path or str(default_db_path())
        self.active_db_path = str(db_path)
        config = read_channel_config(db_path)
        if config is None:
            if not (os.environ.get("AGENTMAIL_CHANNEL_ROOM") or os.environ.get("AGENTMAIL_CHANNEL_AGENT")):
                return
            config = _default_channel_config()
        if not config.get("enabled", True):
            return
        room_name = str(config.get("room_name") or "default")
        agent_name = str(config.get("agent_name") or "claude")
        updated_at = str(config.get("updated_at") or "")
        key = (str(db_path), room_name, agent_name, updated_at)
        service = AgentMailService(AgentMailStore(db_path))
        messages = service.inbox(agent_name, room_name, include_resolved=False, include_seen=False, limit=50)
        if key != self._channel_key:
            self._channel_key = key
            self._channel_seen = set()
        fresh = [message for message in reversed(messages) if message["id"] not in self._channel_seen]
        for message in fresh:
            self._channel_seen.add(message["id"])
            if message.get("from_agent") == agent_name:
                continue
            self._emit_channel_message(room_name, agent_name, message)

    def _emit_channel_message(self, room_name: str, agent_name: str, message: dict[str, Any]) -> None:
        if self._output is None:
            return
        self._output(channel_notification_for_message(room_name, message))
        if message.get("status") == "queued":
            try:
                AgentMailService(AgentMailStore(self.active_db_path or default_db_path())).mark(
                    message["id"],
                    "delivered",
                    agent_name,
                )
            except Exception as exc:  # pragma: no cover - delivery succeeded; status update is best effort
                print(f"agentmail channel mark error: {exc}", file=sys.stderr, flush=True)

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        try:
            if method == "initialize":
                capabilities: dict[str, Any] = {"tools": {}}
                if self.channel_enabled:
                    capabilities["experimental"] = {"claude/channel": {}}
                self._start_channel_thread()
                return self._result(
                    request_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": capabilities,
                        "serverInfo": {"name": "agentmail", "version": "0.1.0"},
                        "instructions": CHANNEL_INSTRUCTIONS if self.channel_enabled else "",
                    },
                )
            if method == "notifications/initialized":
                return None
            if method == "tools/list":
                return self._result(request_id, {"tools": TOOLS})
            if method == "tools/call":
                params = request.get("params") or {}
                tool_name = params.get("name")
                arguments = params.get("arguments") or {}
                if tool_name not in TOOL_TO_METHOD:
                    raise ValueError(f"unknown tool: {tool_name}")
                result = call_method(self._db_path_for_call(arguments), TOOL_TO_METHOD[tool_name], arguments)
                if tool_name == "agentmail_join" and self.channel_enabled and arguments.get("agent_kind") == "claude":
                    result["channel"] = write_channel_config(
                        self._db_path_for_call(arguments) or default_db_path(),
                        arguments.get("room_name", "default"),
                        arguments["agent_name"],
                    )
                return self._result(
                    request_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
                            }
                        ],
                        "structuredContent": result,
                        "isError": False,
                    },
                )
            return self._error(request_id, -32601, f"method not found: {method}")
        except Exception as exc:
            return self._error(request_id, -32000, str(exc))

    def close(self) -> None:
        self._channel_stop.set()
        if self._channel_thread:
            self._channel_thread.join(timeout=2)

    def _result(self, request_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


CHANNEL_INSTRUCTIONS = (
    "AgentMail channel events arrive as <channel source=\"agentmail\" ...>. "
    "Each event is a peer message from another local coding agent in the same repository. "
    "The event body is the exact AgentMail message body; preserve it as opaque natural language. "
    "Use the message_id/from_agent/room/thread_id/subject attributes for routing. "
    "When you handle a message, use AgentMail tools such as agentmail_mark and agentmail_reply."
)


def channel_notification_for_message(room_name: str, message: dict[str, Any]) -> dict[str, Any]:
    meta = {
        "room": room_name,
        "message_id": str(message.get("id", "")),
        "from_agent": str(message.get("from_agent", "")),
        "thread_id": str(message.get("thread_id", "")),
        "trace_id": str(message.get("trace_id", "")),
        "subject": str(message.get("subject", "")),
    }
    return {
        "jsonrpc": "2.0",
        "method": "notifications/claude/channel",
        "params": {
            "content": str(message.get("body", "")),
            "meta": meta,
        },
    }


def _default_channel_config() -> dict[str, Any]:
    return {
        "enabled": True,
        "room_name": os.environ.get("AGENTMAIL_CHANNEL_ROOM", "default"),
        "agent_name": os.environ.get("AGENTMAIL_CHANNEL_AGENT", "claude"),
        "updated_at": _CHANNEL_PROCESS_STARTED_AT,
    }


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def run_stdio_server(db_path: str | None = None) -> None:
    output_lock = threading.Lock()

    def write_message(message: dict[str, Any]) -> None:
        with output_lock:
            sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    server = AgentMailMCP(db_path, output=write_message)
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            response = server.handle_request(json.loads(line))
            if response is not None:
                write_message(response)
    finally:
        server.close()


def main() -> int:
    run_stdio_server(os.environ.get("AGENTMAIL_DB"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
