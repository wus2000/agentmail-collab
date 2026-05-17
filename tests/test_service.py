from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmail.service import AgentMailError, AgentMailService, ConflictError
from agentmail.store import AgentMailStore, utc_now


class AgentMailServiceTests(unittest.TestCase):
    def make_service(self, temp_dir: str) -> AgentMailService:
        return AgentMailService(AgentMailStore(Path(temp_dir) / "agentmail.db"))

    def join_pair(self, service: AgentMailService) -> None:
        service.join("claude", "claude", "shop", workspace=".")
        service.join("codex", "codex", "shop", workspace=".")

    def test_join_peers_send_reply_and_read_thread(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)

            peers = service.peers("shop")
            self.assertEqual([peer["name"] for peer in peers], ["claude", "codex"])

            sent = service.send(
                from_agent="codex",
                to_agents=["claude"],
                room_name="shop",
                thread_title="main",
                subject="Plan ecommerce admin",
                body="Please think through risks.",
                tags=["planning"],
            )
            message_id = sent["message"]["id"]

            inbox = service.inbox("claude", "shop")
            self.assertEqual(len(inbox), 1)
            self.assertEqual(inbox[0]["subject"], "Plan ecommerce admin")
            self.assertEqual(inbox[0]["status"], "queued")

            marked = service.mark(message_id, "claimed", "claude")
            self.assertEqual(marked["message"]["status"], "claimed")

            reply = service.reply(message_id, "claude", "I will cover architecture risks.")
            self.assertEqual(reply["message"]["to_agents"], ["codex"])

            thread = service.read_thread("shop", "main")
            self.assertEqual(len(thread["messages"]), 2)
            self.assertEqual(thread["messages"][0]["status"], "replied")
            self.assertEqual(thread["messages"][1]["parent_message_id"], message_id)

    def test_message_body_is_opaque_and_preserved_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)
            body = "  leading space\n\n```json\n{\"a\": 1}\n```\ntrailing space  \n"
            reply_body = "\n  reply keeps whitespace  \n"

            sent = service.send("codex", ["claude"], "shop", "main", "Opaque", body)
            message_id = sent["message"]["id"]
            service.reply(message_id, "claude", reply_body)

            thread = service.read_thread("shop", "main")
            self.assertEqual(thread["messages"][0]["body"], body)
            self.assertEqual(thread["messages"][1]["body"], reply_body)

    def test_empty_body_is_allowed_as_agent_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)

            sent = service.send("codex", ["claude"], "shop", "main", "Signal", "")

            self.assertEqual(sent["message"]["body"], "")

    def test_note_broadcast_uses_wildcard_recipient(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)

            note = service.note("claude", "shop", "main", "Shared decision: start small.")

            self.assertEqual(note["message"]["to_agents"], ["*"])
            self.assertEqual(service.inbox("codex", "shop")[0]["body"], "Shared decision: start small.")
            self.assertEqual(service.inbox("claude", "shop"), [])

    def test_join_can_send_deduplicated_discovery_to_existing_peers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            service.join("claude", "claude", "shop", workspace=temp_dir, capabilities=["peer-mailbox"])

            joined = service.join(
                "codex",
                "codex",
                "shop",
                workspace=temp_dir,
                capabilities=["peer-mailbox", "active-wakeup"],
                announce_discovery=True,
            )
            repeated = service.join(
                "codex",
                "codex",
                "shop",
                workspace=temp_dir,
                capabilities=["peer-mailbox", "active-wakeup"],
                announce_discovery=True,
            )

            self.assertEqual(joined["discovery"]["to_agents"], ["claude"])
            self.assertEqual(joined["discovery"]["expects_reply"], False)
            self.assertIn("agentmail-discovery", joined["discovery"]["tags"])
            self.assertNotIn("discovery", repeated)
            inbox = service.inbox("claude", "shop")
            self.assertEqual(len(inbox), 1)
            self.assertEqual(inbox[0]["subject"], "AgentMail discovery: codex joined shop")
            self.assertIn("Agent `codex` joined room `shop`.", inbox[0]["body"])

    def test_scope_claim_conflict_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)

            first = service.claim_scope("codex", "shop", ["src/orders.py"], "Implement orders")
            self.assertEqual(first["claim"]["status"], "active")

            with self.assertRaises(ConflictError):
                service.claim_scope("claude", "shop", ["src/orders.py"], "Review and edit")

            released = service.release_scope("codex", "shop", ["src/orders.py"])
            self.assertEqual(len(released["released"]), 1)

            second = service.claim_scope("claude", "shop", ["src/orders.py"], "Review after release")
            self.assertEqual(second["claim"]["paths"], ["src/orders.py"])

    def test_scope_claim_detects_parent_child_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)

            service.claim_scope("codex", "shop", ["src/orders"], "Implement orders package")

            with self.assertRaises(ConflictError):
                service.claim_scope("claude", "shop", ["src/orders/model.py"], "Review model")

    def test_mark_requires_known_agent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)
            message = service.send("codex", ["claude"], "shop", "main", "Hello", "Body")["message"]

            with self.assertRaises(Exception):
                service.mark(message["id"], "seen", "unknown")

    def test_timeline_records_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)
            service.send("codex", ["claude"], "shop", "main", "Hello", "Body")

            timeline = service.timeline("shop", limit=10)

            event_types = {event["event_type"] for event in timeline}
            self.assertIn("agent.joined", event_types)
            self.assertIn("message.sent", event_types)

    def test_room_status_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)

            paused = service.set_room_status("shop", "paused", "claude")
            self.assertEqual(paused["room"]["status"], "paused")

            artifact = service.add_artifact(
                room_name="shop",
                thread_title="main",
                created_by="codex",
                artifact_type="log",
                path=".agentmail/artifacts/test.log",
                summary="Test run output",
            )
            self.assertEqual(artifact["artifact"]["type"], "log")

            artifacts = service.artifacts("shop", "main")
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0]["summary"], "Test run output")

            event_types = {event["event_type"] for event in service.timeline("shop", limit=10)}
            self.assertIn("room.paused", event_types)
            self.assertIn("artifact.added", event_types)

    def test_status_includes_db_path_peers_inbox_and_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)
            service.send("codex", ["claude"], "shop", "main", "Hello", "Body")
            service.claim_scope("codex", "shop", ["src/orders"], "Implement orders")

            status = service.status("shop", "claude")

            self.assertTrue(status["db_path"].endswith("agentmail.db"))
            self.assertEqual([peer["name"] for peer in status["peers"]], ["claude", "codex"])
            self.assertEqual(status["inbox"][0]["subject"], "Hello")
            self.assertEqual(status["active_claims"][0]["paths"], ["src/orders"])

    def test_inbox_paginates_until_addressed_messages_are_found(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)
            service.join("reviewer", "other", "shop", workspace=".")
            target = service.send("codex", ["claude"], "shop", "main", "Target", "Body")["message"]
            for index in range(125):
                service.send("codex", ["reviewer"], "shop", "main", f"Noise {index}", "Body", expects_reply=False)

            inbox = service.inbox("claude", "shop", limit=1)

            self.assertEqual(len(inbox), 1)
            self.assertEqual(inbox[0]["id"], target["id"])

    def test_closed_room_rejects_new_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)
            service.set_room_status("shop", "closed", "claude")

            with self.assertRaises(AgentMailError):
                service.send("codex", ["claude"], "shop", "main", "After close", "Body")

    def test_closed_room_rejects_replies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            self.join_pair(service)
            message = service.send("codex", ["claude"], "shop", "main", "Before close", "Body")["message"]
            service.set_room_status("shop", "closed", "claude")

            with self.assertRaises(AgentMailError):
                service.reply(message["id"], "claude", "Reply after close")

    def test_timestamps_include_microseconds(self) -> None:
        self.assertRegex(utc_now(), r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


if __name__ == "__main__":
    unittest.main()
