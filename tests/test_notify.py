from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agentmail.notify import start_watcher


class AgentMailNotifyTests(unittest.TestCase):
    def test_start_watcher_does_not_enable_os_notifications_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            process = Mock()
            process.pid = 12345

            with patch("agentmail.notify.subprocess.Popen", return_value=process) as popen:
                start_watcher(db, "shop", "claude")

            cmd = popen.call_args.args[0]
            self.assertNotIn("--notify", cmd)

    def test_start_watcher_can_opt_into_os_notifications(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "agentmail.db"
            process = Mock()
            process.pid = 12345

            with patch("agentmail.notify.subprocess.Popen", return_value=process) as popen:
                start_watcher(db, "shop", "claude", notify=True)

            cmd = popen.call_args.args[0]
            self.assertIn("--notify", cmd)


if __name__ == "__main__":
    unittest.main()
