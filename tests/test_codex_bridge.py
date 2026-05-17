from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agentmail.codex_bridge import (
    CodexBridgeError,
    _WebSocket,
    _ready_url,
    bridge_status,
    deliver_message,
    format_codex_input,
    poll_once,
    start_bridge,
)
from agentmail.service import AgentMailService
from agentmail.store import AgentMailStore


class FakeCodexClient:
    def __init__(self, loaded_threads: list[str] | None = None) -> None:
        self.loaded_threads = loaded_threads or []
        self.calls: list[tuple[str, dict]] = []

    def request(self, method: str, params: dict) -> dict:
        self.calls.append((method, params))
        if method == "thread/loaded/list":
            return {"data": self.loaded_threads, "nextCursor": None}
        if method == "thread/start":
            return {"thread": {"id": "thread-created"}}
        if method == "turn/start":
            return {"turn": {"id": "turn-1"}}
        if method == "thread/inject_items":
            return {}
        raise AssertionError(f"unexpected method: {method}")


class FlakyCodexClient(FakeCodexClient):
    def __init__(self) -> None:
        super().__init__(["thread-1"])
        self.failures_remaining = 1

    def request(self, method: str, params: dict) -> dict:
        if method == "turn/start" and self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("temporary app-server outage")
        return super().request(method, params)


class AgentMailCodexBridgeTests(unittest.TestCase):
    def test_format_codex_input_preserves_body(self) -> None:
        body = "json: {\"a\": 1}\n```txt\n<channel> & symbols\n```"
        text = format_codex_input(
            {
                "id": "msg_1",
                "from_agent": "claude",
                "subject": "Freeform",
                "body": body,
            }
        )

        self.assertIn('"message_id": "msg_1"', text)
        envelope = _extract_envelope(text)
        begin = envelope["body_fence_begin"]
        end = envelope["body_fence_end"]
        self.assertTrue(begin.startswith("---BEGIN_AGENTMAIL_BODY_"))
        self.assertTrue(end.startswith("---END_AGENTMAIL_BODY_"))
        self.assertIn(begin + "\n" + body + "\n" + end, text)

    def test_format_codex_input_randomizes_body_fences(self) -> None:
        body = "contains old fixed fence\n---END_AGENTMAIL_BODY---\nand continues"
        text = format_codex_input({"id": "msg_1", "body": body})

        envelope = _extract_envelope(text)
        begin = envelope["body_fence_begin"]
        end = envelope["body_fence_end"]
        self.assertNotEqual(begin, "---BEGIN_AGENTMAIL_BODY---")
        self.assertNotEqual(end, "---END_AGENTMAIL_BODY---")
        self.assertNotIn(begin, body)
        self.assertNotIn(end, body)
        self.assertIn(begin + "\n" + body + "\n" + end, text)

    def test_deliver_message_uses_loaded_thread_and_turn_start(self) -> None:
        client = FakeCodexClient(["thread-1"])
        result = deliver_message(
            {"id": "msg_1", "from_agent": "claude", "subject": "Wake", "body": "Please inspect this."},
            workspace="/tmp/work",
            client=client,  # type: ignore[arg-type]
        )

        self.assertEqual(result["thread_id"], "thread-1")
        self.assertEqual(client.calls[0][0], "thread/loaded/list")
        self.assertEqual(client.calls[1][0], "turn/start")
        self.assertEqual(client.calls[1][1]["threadId"], "thread-1")
        self.assertIn("Please inspect this.", client.calls[1][1]["input"][0]["text"])

    def test_deliver_message_can_start_thread_and_inject(self) -> None:
        client = FakeCodexClient([])
        result = deliver_message(
            {"id": "msg_1", "from_agent": "claude", "subject": "Context", "body": "Record only."},
            workspace="/tmp/work",
            mode="inject",
            client=client,  # type: ignore[arg-type]
        )

        self.assertEqual(result["thread_id"], "thread-created")
        self.assertEqual([method for method, _ in client.calls], ["thread/loaded/list", "thread/start", "thread/inject_items"])
        injected = client.calls[-1][1]["items"][0]
        self.assertEqual(injected["role"], "user")
        self.assertIn("Record only.", injected["content"][0]["text"])

    def test_deliver_message_rejects_ambiguous_loaded_threads(self) -> None:
        client = FakeCodexClient(["thread-1", "thread-2"])

        with self.assertRaises(CodexBridgeError):
            deliver_message(
                {"id": "msg_1", "from_agent": "claude", "subject": "Wake", "body": "Please inspect this."},
                workspace="/tmp/work",
                client=client,  # type: ignore[arg-type]
            )

    def test_poll_once_marks_delivered_after_successful_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            service = AgentMailService(AgentMailStore(db))
            service.join("claude", "claude", "shop", temp_dir, [])
            service.join("codex", "codex", "shop", temp_dir, [])
            sent = service.send("claude", ["codex"], "shop", "main", "Wake", "Body", [], [], True)

            result = poll_once(
                service,
                "shop",
                "codex",
                workspace=temp_dir,
                client=FakeCodexClient(["thread-1"]),  # type: ignore[arg-type]
            )

            self.assertEqual(result["delivered"], 1)
            inbox = service.inbox("codex", "shop", include_resolved=False, include_seen=True)
            self.assertEqual(inbox[0]["id"], sent["message"]["id"])
            self.assertEqual(inbox[0]["status"], "delivered")

    def test_poll_once_retries_failed_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            service = AgentMailService(AgentMailStore(db))
            service.join("claude", "claude", "shop", temp_dir, [])
            service.join("codex", "codex", "shop", temp_dir, [])
            sent = service.send("claude", ["codex"], "shop", "main", "Wake", "Body", [], [], True)
            seen: set[str] = set()
            client = FlakyCodexClient()

            first = poll_once(
                service,
                "shop",
                "codex",
                workspace=temp_dir,
                seen=seen,
                client=client,  # type: ignore[arg-type]
            )
            second = poll_once(
                service,
                "shop",
                "codex",
                workspace=temp_dir,
                seen=seen,
                client=client,  # type: ignore[arg-type]
            )

            self.assertEqual(first["delivered"], 0)
            self.assertEqual(len(first["errors"]), 1)
            self.assertEqual(second["delivered"], 1)
            inbox = service.inbox("codex", "shop", include_resolved=False, include_seen=True)
            self.assertEqual(inbox[0]["id"], sent["message"]["id"])
            self.assertEqual(inbox[0]["status"], "delivered")

    def test_poll_once_skips_self_sent_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            service = AgentMailService(AgentMailStore(db))
            service.join("codex", "codex", "shop", temp_dir, [])
            sent = service.send("codex", ["codex"], "shop", "main", "Self", "Body", [], [], True)
            client = FakeCodexClient(["thread-1"])

            result = poll_once(
                service,
                "shop",
                "codex",
                workspace=temp_dir,
                client=client,  # type: ignore[arg-type]
            )

            self.assertEqual(result["delivered"], 0)
            self.assertEqual(client.calls, [])
            inbox = service.inbox("codex", "shop", include_resolved=False, include_seen=True)
            self.assertEqual(inbox[0]["id"], sent["message"]["id"])
            self.assertEqual(inbox[0]["status"], "queued")

    def test_start_bridge_spawns_managed_app_server_and_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            app_proc = Mock()
            app_proc.pid = 111
            bridge_proc = Mock()
            bridge_proc.pid = 222

            with (
                patch("agentmail.codex_bridge.shutil.which", return_value="/usr/local/bin/codex"),
                patch("agentmail.codex_bridge.subprocess.Popen", side_effect=[app_proc, bridge_proc]) as popen,
                patch("agentmail.codex_bridge.wait_for_app_server", return_value=True),
                patch("agentmail.codex_bridge.pid_alive", return_value=False),
            ):
                status = start_bridge(db, "shop", "codex", workspace=temp_dir, listen="ws://127.0.0.1:4999")

            self.assertTrue(status["started"])
            self.assertEqual(popen.call_args_list[0].args[0][:3], ["codex", "app-server", "--listen"])
            self.assertIn("codex-bridge", popen.call_args_list[1].args[0])
            self.assertEqual(bridge_status(db, "shop", "codex")["config"]["listen"], "ws://127.0.0.1:4999")

    def test_ready_url_skips_remote_endpoints(self) -> None:
        self.assertEqual(_ready_url("ws://127.0.0.1:4999"), "http://127.0.0.1:4999/readyz")
        self.assertEqual(_ready_url("wss://example.com:443"), "")

    def test_websocket_recv_text_supports_continuation_frames(self) -> None:
        frames = _server_frame(0x1, b'{"id":', fin=False) + _server_frame(0x0, b'1,"result":{}}', fin=True)
        ws = _WebSocket(_FakeSocket(frames))  # type: ignore[arg-type]

        self.assertEqual(ws.recv_json(), {"id": 1, "result": {}})


class _FakeSocket:
    def __init__(self, data: bytes) -> None:
        self.data = bytearray(data)
        self.sent = bytearray()

    def recv(self, count: int) -> bytes:
        chunk = self.data[:count]
        del self.data[:count]
        return bytes(chunk)

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def close(self) -> None:
        pass


def _server_frame(opcode: int, payload: bytes, *, fin: bool) -> bytes:
    first = (0x80 if fin else 0) | opcode
    if len(payload) < 126:
        return bytes([first, len(payload)]) + payload
    if len(payload) <= 0xFFFF:
        return bytes([first, 126]) + len(payload).to_bytes(2, "big") + payload
    return bytes([first, 127]) + len(payload).to_bytes(8, "big") + payload


def _extract_envelope(text: str) -> dict:
    lines = text.splitlines()
    index = lines.index("Envelope:")
    return json.loads(lines[index + 1])


if __name__ == "__main__":
    unittest.main()
