from __future__ import annotations

import tempfile
import json
import threading
import unittest
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

from agentmail.daemon import AgentMailHandler, call_method


class AgentMailDaemonTests(unittest.TestCase):
    def test_json_rpc_method_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = str(Path(temp_dir) / "agentmail.db")
            call_method(db, "join", {"agent_name": "claude", "agent_kind": "claude", "room_name": "shop"})
            call_method(db, "join", {"agent_name": "codex", "agent_kind": "codex", "room_name": "shop"})
            sent = call_method(
                db,
                "send",
                {
                    "from_agent": "claude",
                    "to_agents": ["codex"],
                    "room_name": "shop",
                    "body": "Can you implement the first slice?",
                },
            )
            inbox = call_method(db, "inbox", {"agent_name": "codex", "room_name": "shop"})
            self.assertEqual(inbox[0]["id"], sent["message"]["id"])

    def test_join_uses_workspace_when_db_is_not_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            call_method(
                None,
                "join",
                {
                    "agent_name": "codex",
                    "agent_kind": "codex",
                    "room_name": "shop",
                    "workspace": workspace,
                },
            )
            db = Path(workspace) / ".agentmail" / "agentmail.db"
            peers = call_method(str(db), "peers", {"room_name": "shop"})
            self.assertEqual(peers[0]["name"], "codex")

    def test_http_rpc_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            AgentMailHandler.db_path = str(Path(temp_dir) / "agentmail.db")
            server = ThreadingHTTPServer(("127.0.0.1", 0), AgentMailHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"
                self._post(base, "join", {"agent_name": "claude", "agent_kind": "claude", "room_name": "shop"})
                self._post(base, "join", {"agent_name": "codex", "agent_kind": "codex", "room_name": "shop"})
                self._post(
                    base,
                    "send",
                    {
                        "from_agent": "codex",
                        "to_agents": ["claude"],
                        "room_name": "shop",
                        "body": "Need review.",
                    },
                )
                inbox = self._post(base, "inbox", {"agent_name": "claude", "room_name": "shop"})
                self.assertEqual(inbox["ok"], True)
                self.assertEqual(inbox["result"][0]["body"], "Need review.")
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

    def _post(self, base: str, method: str, params: dict) -> dict:
        body = json.dumps({"method": method, "params": params}).encode("utf-8")
        request = urllib.request.Request(
            f"{base}/rpc",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
