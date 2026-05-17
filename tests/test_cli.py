from __future__ import annotations

import io
import json
import os
import time
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agentmail import cli


class AgentMailCliTests(unittest.TestCase):
    def run_cli(self, db: Path, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            rc = cli.main(["--db", str(db), "--json", *args])
        return rc, output.getvalue()

    def run_cli_text(self, db: Path, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            rc = cli.main(["--db", str(db), *args])
        return rc, output.getvalue()

    def test_cli_join_send_inbox_reply(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"

            self.assertEqual(self.run_cli(db, "join", "--agent", "claude", "--kind", "claude", "--room", "shop")[0], 0)
            self.assertEqual(self.run_cli(db, "join", "--agent", "codex", "--kind", "codex", "--room", "shop")[0], 0)

            rc, sent_text = self.run_cli(
                db,
                "send",
                "--from",
                "codex",
                "--to",
                "claude",
                "--room",
                "shop",
                "--subject",
                "Question",
                "--body",
                "How should we split work?",
            )
            self.assertEqual(rc, 0)
            message_id = json.loads(sent_text)["message"]["id"]

            rc, inbox_text = self.run_cli(db, "inbox", "--agent", "claude", "--room", "shop")
            self.assertEqual(rc, 0)
            inbox = json.loads(inbox_text)
            self.assertEqual(inbox[0]["id"], message_id)

            rc, reply_text = self.run_cli(
                db,
                "reply",
                "--agent",
                "claude",
                "--message",
                message_id,
                "--body",
                "I will own architecture review.",
            )
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(reply_text)["message"]["to_agents"], ["codex"])

            rc, artifact_text = self.run_cli(
                db,
                "artifact-add",
                "--agent",
                "codex",
                "--room",
                "shop",
                "--type",
                "diff",
                "--path",
                ".agentmail/artifacts/change.patch",
                "--summary",
                "Proposed patch",
            )
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(artifact_text)["artifact"]["type"], "diff")

    def test_cli_start_joins_and_reports_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"

            rc, start_text = self.run_cli(
                db,
                "start",
                "--agent",
                "codex",
                "--kind",
                "codex",
                "--room",
                "shop",
                "--workspace",
                temp_dir,
            )

            self.assertEqual(rc, 0)
            started = json.loads(start_text)
            self.assertEqual(started["joined"]["agent"]["name"], "codex")
            self.assertEqual(started["peers"][0]["name"], "codex")
            self.assertEqual(started["inbox"], [])
            self.assertIsNone(started["channel"])

    def test_cli_start_writes_claude_channel_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"

            rc, start_text = self.run_cli(
                db,
                "start",
                "--agent",
                "claude",
                "--kind",
                "claude",
                "--room",
                "shop",
                "--workspace",
                temp_dir,
            )

            self.assertEqual(rc, 0)
            started = json.loads(start_text)
            self.assertEqual(started["channel"]["config"]["room_name"], "shop")
            self.assertEqual(started["channel"]["config"]["agent_name"], "claude")
            self.assertTrue((db.parent / "channel.json").exists())

    def test_cli_start_uses_workspace_for_default_db(self) -> None:
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as other_dir:
            previous = os.getcwd()
            try:
                os.chdir(other_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    rc = cli.main(
                        [
                            "--json",
                            "start",
                            "--agent",
                            "codex",
                            "--kind",
                            "codex",
                            "--room",
                            "shop",
                            "--workspace",
                            workspace,
                        ]
                    )
            finally:
                os.chdir(previous)

            self.assertEqual(rc, 0)
            self.assertTrue((Path(workspace) / ".agentmail" / "agentmail.db").exists())
            self.assertFalse((Path(other_dir) / ".agentmail" / "agentmail.db").exists())

    def test_cli_status_and_notify_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            self.run_cli(db, "join", "--agent", "claude", "--kind", "claude", "--room", "shop")

            rc, status_text = self.run_cli(db, "status", "--agent", "claude", "--room", "shop")
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(status_text)["agent"], "claude")

            rc, start_text = self.run_cli(db, "notify-start", "--agent", "claude", "--room", "shop", "--no-notify")
            self.assertEqual(rc, 0)
            started = json.loads(start_text)
            self.assertEqual(started["running"], True)
            time.sleep(0.2)

            rc, notify_status_text = self.run_cli(db, "notify-status", "--agent", "claude", "--room", "shop")
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(notify_status_text)["running"], True)

            rc, text_status = self.run_cli_text(db, "notify-status", "--agent", "claude", "--room", "shop")
            self.assertEqual(rc, 0)
            self.assertIn('"running": true', text_status)

            rc, stop_text = self.run_cli(db, "notify-stop", "--agent", "claude", "--room", "shop")
            self.assertEqual(rc, 0)
            self.assertIn("stopped", json.loads(stop_text))

    def test_cli_body_file_preserves_exact_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            body_path = Path(temp_dir) / "body.md"
            exact_body = "  first line\n\n- bullet\nlast line  \n"
            body_path.write_text(exact_body, encoding="utf-8")

            self.run_cli(db, "join", "--agent", "claude", "--kind", "claude", "--room", "shop")
            self.run_cli(db, "join", "--agent", "codex", "--kind", "codex", "--room", "shop")
            self.run_cli(
                db,
                "send",
                "--from",
                "codex",
                "--to",
                "claude",
                "--room",
                "shop",
                "--subject",
                "Opaque",
                "--body-file",
                str(body_path),
            )

            _, inbox_text = self.run_cli(db, "inbox", "--agent", "claude", "--room", "shop")
            self.assertEqual(json.loads(inbox_text)[0]["body"], exact_body)

    def test_bootstrap_codex_prepares_workspace_and_prints_launch_command(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            db = Path(workspace) / ".agentmail" / "agentmail.db"

            rc, text = self.run_cli(
                db,
                "bootstrap-codex",
                "--agent",
                "codex",
                "--room",
                "shop",
                "--workspace",
                workspace,
                "--listen",
                "ws://127.0.0.1:4999",
                "--dry-run",
                "--no-open-terminal",
            )

            self.assertEqual(rc, 0)
            result = json.loads(text)
            self.assertFalse(result["opened_terminal"])
            self.assertEqual(result["listen"], "ws://127.0.0.1:4999")
            self.assertIn("launch-codex", result["command"])
            self.assertIn("--room shop", result["command"])
            self.assertEqual(result["joined"]["agent"]["name"], "codex")

            rc, peers_text = self.run_cli(db, "peers", "--room", "shop")
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(peers_text)[0]["name"], "codex")

    def test_doctor_reports_workspace_database_and_peers(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            db = Path(workspace) / ".agentmail" / "agentmail.db"
            self.run_cli(db, "start", "--agent", "claude", "--kind", "claude", "--room", "shop", "--workspace", workspace)

            rc, text = self.run_cli(db, "doctor", "--room", "shop", "--workspace", workspace)

            self.assertEqual(rc, 0)
            result = json.loads(text)
            self.assertEqual(result["db_path"], str(db))
            self.assertEqual(result["peers"][0]["name"], "claude")
            checks = {check["name"]: check for check in result["checks"]}
            self.assertTrue(checks["workspace_exists"]["ok"])
            self.assertTrue(checks["database_exists"]["ok"])


if __name__ == "__main__":
    unittest.main()
