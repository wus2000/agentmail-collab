"""AgentMail: local peer-to-peer mailbox primitives for coding agents."""

from agentmail.service import AgentMailService
from agentmail.store import AgentMailStore, default_db_path

__all__ = ["AgentMailService", "AgentMailStore", "default_db_path"]
