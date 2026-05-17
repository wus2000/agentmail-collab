"""Small localhost JSON RPC daemon for AgentMail."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from agentmail.codex_bridge import bridge_status, start_bridge, stop_bridge
from agentmail.notify import start_watcher, stop_watcher, watcher_status
from agentmail.service import AgentMailError, AgentMailService
from agentmail.store import AgentMailStore, default_db_path


def resolve_db_path(db_path: str | None, params: dict[str, Any] | None = None) -> str:
    if db_path:
        return db_path
    workspace = (params or {}).get("workspace")
    return str(default_db_path(workspace))


def _service(db_path: str | None, params: dict[str, Any] | None = None) -> AgentMailService:
    return AgentMailService(AgentMailStore(resolve_db_path(db_path, params)))


def call_method(db_path: str | None, method: str, params: dict[str, Any]) -> Any:
    service = _service(db_path, params)
    methods = {
        "join": lambda: service.join(
            params["agent_name"],
            params["agent_kind"],
            params.get("room_name", "default"),
            params.get("workspace", "."),
            params.get("capabilities", []),
        ),
        "peers": lambda: service.peers(params.get("room_name", "default")),
        "status": lambda: service.status(
            params.get("room_name", "default"),
            params.get("agent_name"),
            params.get("limit", 20),
        ),
        "set_room_status": lambda: service.set_room_status(
            params.get("room_name", "default"),
            params["status"],
            params["actor"],
        ),
        "send": lambda: service.send(
            params["from_agent"],
            params["to_agents"],
            params.get("room_name", "default"),
            params.get("thread_title", "main"),
            params.get("subject", ""),
            params["body"],
            params.get("refs", []),
            params.get("tags", []),
            params.get("expects_reply", True),
            params.get("parent_message_id", ""),
        ),
        "inbox": lambda: service.inbox(
            params["agent_name"],
            params.get("room_name", "default"),
            params.get("include_resolved", False),
            params.get("include_seen", True),
            params.get("limit", 50),
        ),
        "read_thread": lambda: service.read_thread(params.get("room_name", "default"), params.get("thread", "main")),
        "mark": lambda: service.mark(params["message_id"], params["status"], params["actor"]),
        "reply": lambda: service.reply(
            params["message_id"],
            params["from_agent"],
            params["body"],
            params.get("refs", []),
            params.get("tags", []),
            params.get("resolve_original", False),
        ),
        "note": lambda: service.note(
            params["from_agent"],
            params.get("room_name", "default"),
            params.get("thread_title", "main"),
            params["body"],
            params.get("refs", []),
            params.get("tags", []),
        ),
        "add_artifact": lambda: service.add_artifact(
            params.get("room_name", "default"),
            params.get("thread_title", "main"),
            params["created_by"],
            params.get("artifact_type", "file"),
            params["path"],
            params.get("summary", ""),
        ),
        "artifacts": lambda: service.artifacts(
            params.get("room_name", "default"),
            params.get("thread"),
            params.get("limit", 50),
        ),
        "claim_scope": lambda: service.claim_scope(
            params["agent_name"],
            params.get("room_name", "default"),
            params["paths"],
            params.get("reason", ""),
            params.get("ttl_seconds", 3600),
            params.get("force", False),
        ),
        "release_scope": lambda: service.release_scope(
            params["agent_name"],
            params.get("room_name", "default"),
            params.get("paths", []),
        ),
        "notify_start": lambda: start_watcher(
            resolve_db_path(db_path, params),
            params.get("room_name", "default"),
            params["agent_name"],
            params.get("interval", 2.0),
            params.get("notify", False),
            params.get("command", ""),
            params.get("since_now", True),
        ),
        "notify_stop": lambda: stop_watcher(
            resolve_db_path(db_path, params),
            params.get("room_name", "default"),
            params["agent_name"],
        ),
        "notify_status": lambda: watcher_status(
            resolve_db_path(db_path, params),
            params.get("room_name", "default"),
            params["agent_name"],
        ),
        "codex_bridge_start": lambda: start_bridge(
            resolve_db_path(db_path, params),
            params.get("room_name", "default"),
            params.get("agent_name", "codex"),
            workspace=params.get("workspace", "."),
            listen=params.get("listen", "ws://127.0.0.1:4500"),
            thread_id=params.get("thread_id", ""),
            mode=params.get("mode", "turn-start"),
            interval=params.get("interval", 2.0),
            since_now=params.get("since_now", True),
            start_app_server=params.get("start_app_server", True),
        ),
        "codex_bridge_stop": lambda: stop_bridge(
            resolve_db_path(db_path, params),
            params.get("room_name", "default"),
            params.get("agent_name", "codex"),
        ),
        "codex_bridge_status": lambda: bridge_status(
            resolve_db_path(db_path, params),
            params.get("room_name", "default"),
            params.get("agent_name", "codex"),
        ),
        "timeline": lambda: service.timeline(params.get("room_name", "default"), params.get("limit", 50)),
    }
    if method not in methods:
        raise AgentMailError(f"unknown method: {method}")
    return methods[method]()


class AgentMailHandler(BaseHTTPRequestHandler):
    db_path: str | None = None

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/healthz", "/readyz"}:
            self._send_json({"ok": True})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/rpc":
            self._send_json({"error": "not found"}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = call_method(self.db_path, payload["method"], payload.get("params", {}))
            self._send_json({"ok": True, "result": result})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = "127.0.0.1", port: int = 8765, db_path: str | None = None) -> None:
    AgentMailHandler.db_path = db_path
    server = ThreadingHTTPServer((host, port), AgentMailHandler)
    print(f"agentmaild listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
