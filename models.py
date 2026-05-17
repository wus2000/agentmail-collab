"""Domain models for AgentMail.

These models deliberately describe generic collaboration primitives. They do
not encode a planning/review/implementation workflow; agents decide that in
natural language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Agent:
    id: str
    room_id: str
    name: str
    kind: str
    workspace: str
    status: str
    capabilities: list[str] = field(default_factory=list)
    created_at: str = ""
    last_seen: str = ""


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    workspace: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Thread:
    id: str
    room_id: str
    title: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Message:
    id: str
    room_id: str
    thread_id: str
    from_agent: str
    to_agents: list[str]
    subject: str
    body: str
    status: str
    expects_reply: bool
    parent_message_id: str = ""
    trace_id: str = ""
    tags: list[str] = field(default_factory=list)
    refs: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ScopeClaim:
    id: str
    room_id: str
    agent_id: str
    paths: list[str]
    reason: str
    status: str
    expires_at: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Artifact:
    id: str
    room_id: str
    thread_id: str
    type: str
    path: str
    summary: str
    created_by: str
    created_at: str
