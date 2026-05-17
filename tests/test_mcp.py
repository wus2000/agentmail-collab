from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentmail.mcp_server import AgentMailMCP, channel_notification_for_message
from agentmail.notify import write_channel_config


class AgentMailMcpTests(unittest.TestCase):
    def call(self, server: AgentMailMCP, idx: int, name: str, arguments: dict) -> dict:
        response = server.handle_request(
            {"jsonrpc": "2.0", "id": idx, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        )
        self.assertIsNotNone(response)
        self.assertNotIn("error", response)
        return response["result"]["structuredContent"]

    def test_tool_listing_and_message_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            server = AgentMailMCP(str(Path(temp_dir) / "agentmail.db"))

            listed = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertTrue(any(tool["name"] == "agentmail_send" for tool in listed["result"]["tools"]))
            self.assertTrue(any(tool["name"] == "agentmail_notify_start" for tool in listed["result"]["tools"]))

            self.call(server, 2, "agentmail_join", {"agent_name": "claude", "agent_kind": "claude", "room_name": "shop"})
            self.call(server, 3, "agentmail_join", {"agent_name": "codex", "agent_kind": "codex", "room_name": "shop"})
            sent = self.call(
                server,
                4,
                "agentmail_send",
                {
                    "from_agent": "codex",
                    "to_agents": ["claude"],
                    "room_name": "shop",
                    "subject": "Review",
                    "body": "  Please review the plan.\nKeep spacing.  \n",
                },
            )

            inbox = self.call(server, 5, "agentmail_inbox", {"agent_name": "claude", "room_name": "shop"})
            self.assertEqual(inbox[0]["id"], sent["message"]["id"])
            self.assertEqual(inbox[0]["body"], "  Please review the plan.\nKeep spacing.  \n")

            reply = self.call(
                server,
                6,
                "agentmail_reply",
                {"message_id": sent["message"]["id"], "from_agent": "claude", "body": "Plan looks reasonable."},
            )
            self.assertEqual(reply["message"]["from_agent"], "claude")

            status = self.call(server, 7, "agentmail_status", {"agent_name": "claude", "room_name": "shop"})
            self.assertEqual(status["agent"], "claude")

    def test_join_workspace_binds_default_database_for_followup_calls(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            server = AgentMailMCP()
            self.call(
                server,
                1,
                "agentmail_join",
                {
                    "agent_name": "codex",
                    "agent_kind": "codex",
                    "room_name": "shop",
                    "workspace": workspace,
                },
            )
            peers = self.call(server, 2, "agentmail_peers", {"room_name": "shop"})

            self.assertEqual(peers[0]["name"], "codex")
            self.assertTrue((Path(workspace) / ".agentmail" / "agentmail.db").exists())

    def test_environment_defaults_bind_database_room_and_agent(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            env = {
                "AGENTMAIL_WORKSPACE": workspace,
                "AGENTMAIL_ROOM": "shop",
                "AGENTMAIL_AGENT": "codex",
            }
            with patch.dict(os.environ, env):
                server = AgentMailMCP()
                self.call(server, 1, "agentmail_join", {"agent_name": "codex", "agent_kind": "codex"})
                status = self.call(server, 2, "agentmail_status", {})

            self.assertEqual(status["agent"], "codex")
            self.assertEqual(status["room"]["name"], "shop")
            self.assertEqual(status["db_path"], str(Path(workspace) / ".agentmail" / "agentmail.db"))

    def test_unknown_tool_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            server = AgentMailMCP(str(Path(temp_dir) / "agentmail.db"))
            response = server.handle_request(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "missing", "arguments": {}}}
            )
            self.assertIn("error", response)

    def test_channel_capability_and_notification_preserve_body(self) -> None:
        exact_body = "  hello\n\nKeep this exact.  \n"
        notification = channel_notification_for_message(
            "shop",
            {
                "id": "msg_123",
                "from_agent": "codex",
                "thread_id": "thr_123",
                "trace_id": "trace_123",
                "subject": "Exact",
                "body": exact_body,
            },
        )

        self.assertEqual(notification["method"], "notifications/claude/channel")
        self.assertEqual(notification["params"]["content"], exact_body)
        self.assertEqual(notification["params"]["meta"]["message_id"], "msg_123")

    def test_channel_poll_emits_new_inbox_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            emitted: list[dict] = []
            server = AgentMailMCP(str(db), channel_enabled=True, output=emitted.append)

            self.call(server, 1, "agentmail_join", {"agent_name": "claude", "agent_kind": "claude", "room_name": "shop"})
            self.call(server, 2, "agentmail_join", {"agent_name": "codex", "agent_kind": "codex", "room_name": "shop"})
            write_channel_config(db, "shop", "claude")
            sent = self.call(
                server,
                3,
                "agentmail_send",
                {
                    "from_agent": "codex",
                    "to_agents": ["claude"],
                    "room_name": "shop",
                    "subject": "Wake",
                    "body": "wake up",
                },
            )

            server._poll_channel_once()

            self.assertEqual(len(emitted), 1)
            self.assertEqual(emitted[0]["params"]["content"], "wake up")
            self.assertEqual(emitted[0]["params"]["meta"]["message_id"], sent["message"]["id"])
            inbox = self.call(server, 4, "agentmail_inbox", {"agent_name": "claude", "room_name": "shop"})
            self.assertEqual(inbox[0]["status"], "delivered")


if __name__ == "__main__":
    unittest.main()
