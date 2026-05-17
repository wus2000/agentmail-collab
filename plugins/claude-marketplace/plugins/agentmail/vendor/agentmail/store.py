"""SQLite persistence for AgentMail."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from agentmail.models import Agent, Artifact, Message, Room, ScopeClaim, Thread


VALID_MESSAGE_STATUSES = {
    "queued",
    "delivered",
    "seen",
    "claimed",
    "replied",
    "resolved",
    "cancelled",
    "expired",
    "failed",
}


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"


def default_db_path(workspace: str | os.PathLike[str] | None = None) -> Path:
    override = os.environ.get("AGENTMAIL_DB")
    if override:
        return Path(override).expanduser()
    root_value = (
        workspace
        or os.environ.get("AGENTMAIL_WORKSPACE")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("CODEX_WORKSPACE_ROOT")
        or os.getcwd()
    )
    root = Path(root_value).expanduser()
    return root / ".agentmail" / "agentmail.db"


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


class AgentMailStore:
    """Small repository around a local SQLite database."""

    def __init__(self, db_path: str | os.PathLike[str] | None = None) -> None:
        self.db_path = Path(db_path).expanduser() if db_path else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    workspace TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    status TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    UNIQUE(room_id, name)
                );

                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(room_id, title)
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
                    parent_message_id TEXT NOT NULL DEFAULT '',
                    from_agent TEXT NOT NULL,
                    to_agents_json TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    refs_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expects_reply INTEGER NOT NULL,
                    trace_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
                    type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scope_claims (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                    agent_id TEXT NOT NULL,
                    paths_json TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_room_status
                    ON messages(room_id, status, created_at, id);
                CREATE INDEX IF NOT EXISTS idx_messages_thread
                    ON messages(thread_id, created_at, id);
                CREATE INDEX IF NOT EXISTS idx_claims_room_status
                    ON scope_claims(room_id, status);
                """
            )

    def record_event(
        self,
        conn: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
        event_type: str,
        actor: str,
        data: dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO events(entity_type, entity_id, event_type, actor, data_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entity_type, entity_id, event_type, actor, _json_dumps(data), utc_now()),
        )

    def ensure_room(self, conn: sqlite3.Connection, name: str, workspace: str) -> Room:
        row = conn.execute("SELECT * FROM rooms WHERE name = ?", (name,)).fetchone()
        now = utc_now()
        if row:
            return self._room_from_row(row)
        room = Room(
            id=make_id("room"),
            name=name,
            workspace=workspace,
            status="open",
            created_at=now,
            updated_at=now,
        )
        conn.execute(
            """
            INSERT INTO rooms(id, name, workspace, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (room.id, room.name, room.workspace, room.status, room.created_at, room.updated_at),
        )
        self.record_event(conn, "room", room.id, "room.created", "system", asdict(room))
        return room

    def ensure_thread(self, conn: sqlite3.Connection, room_id: str, title: str) -> Thread:
        row = conn.execute(
            "SELECT * FROM threads WHERE room_id = ? AND title = ?",
            (room_id, title),
        ).fetchone()
        now = utc_now()
        if row:
            return self._thread_from_row(row)
        thread = Thread(
            id=make_id("thr"),
            room_id=room_id,
            title=title,
            status="open",
            created_at=now,
            updated_at=now,
        )
        conn.execute(
            """
            INSERT INTO threads(id, room_id, title, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (thread.id, thread.room_id, thread.title, thread.status, thread.created_at, thread.updated_at),
        )
        self.record_event(conn, "thread", thread.id, "thread.created", "system", asdict(thread))
        return thread

    def find_room(self, conn: sqlite3.Connection, name: str) -> Room | None:
        row = conn.execute("SELECT * FROM rooms WHERE name = ?", (name,)).fetchone()
        return self._room_from_row(row) if row else None

    def find_message(self, conn: sqlite3.Connection, message_id: str) -> Message | None:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        return self._message_from_row(row) if row else None

    def _room_from_row(self, row: sqlite3.Row) -> Room:
        return Room(
            id=row["id"],
            name=row["name"],
            workspace=row["workspace"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _agent_from_row(self, row: sqlite3.Row) -> Agent:
        return Agent(
            id=row["id"],
            room_id=row["room_id"],
            name=row["name"],
            kind=row["kind"],
            workspace=row["workspace"],
            status=row["status"],
            capabilities=_json_loads(row["capabilities_json"], []),
            created_at=row["created_at"],
            last_seen=row["last_seen"],
        )

    def _thread_from_row(self, row: sqlite3.Row) -> Thread:
        return Thread(
            id=row["id"],
            room_id=row["room_id"],
            title=row["title"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _message_from_row(self, row: sqlite3.Row) -> Message:
        return Message(
            id=row["id"],
            room_id=row["room_id"],
            thread_id=row["thread_id"],
            parent_message_id=row["parent_message_id"],
            from_agent=row["from_agent"],
            to_agents=_json_loads(row["to_agents_json"], []),
            subject=row["subject"],
            body=row["body"],
            tags=_json_loads(row["tags_json"], []),
            refs=_json_loads(row["refs_json"], []),
            status=row["status"],
            expects_reply=bool(row["expects_reply"]),
            trace_id=row["trace_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _artifact_from_row(self, row: sqlite3.Row) -> Artifact:
        return Artifact(
            id=row["id"],
            room_id=row["room_id"],
            thread_id=row["thread_id"],
            type=row["type"],
            path=row["path"],
            summary=row["summary"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )

    def _claim_from_row(self, row: sqlite3.Row) -> ScopeClaim:
        return ScopeClaim(
            id=row["id"],
            room_id=row["room_id"],
            agent_id=row["agent_id"],
            paths=_json_loads(row["paths_json"], []),
            reason=row["reason"],
            status=row["status"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def ttl_deadline(self, ttl_seconds: int) -> str:
        return (
            datetime.utcnow()
            + timedelta(seconds=max(ttl_seconds, 1))
        ).isoformat(timespec="microseconds") + "Z"
