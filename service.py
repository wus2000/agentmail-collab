"""Application service for AgentMail use cases."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agentmail.models import Agent, Artifact, Message, Room, ScopeClaim, Thread
from agentmail.store import (
    VALID_MESSAGE_STATUSES,
    AgentMailStore,
    _json_dumps,
    make_id,
    utc_now,
)


class AgentMailError(RuntimeError):
    """Base domain error with a user-actionable message."""


class NotFoundError(AgentMailError):
    pass


class ConflictError(AgentMailError):
    pass


DISCOVERY_TAG = "agentmail-discovery"
DISCOVERY_DEDUP_SECONDS = 300


class AgentMailService:
    """Workflow-free collaboration primitives for peer coding agents."""

    def __init__(self, store: AgentMailStore | None = None) -> None:
        self.store = store or AgentMailStore()

    def join(
        self,
        agent_name: str,
        agent_kind: str,
        room_name: str,
        workspace: str | None = None,
        capabilities: list[str] | None = None,
        announce_discovery: bool = False,
    ) -> dict[str, Any]:
        workspace_root = str(Path(workspace or ".").expanduser().resolve())
        caps = capabilities or []
        with self.store.connect() as conn:
            room = self.store.ensure_room(conn, room_name, workspace_root)
            row = conn.execute(
                "SELECT * FROM agents WHERE room_id = ? AND name = ?",
                (room.id, agent_name),
            ).fetchone()
            now = utc_now()
            if row:
                conn.execute(
                    """
                    UPDATE agents
                    SET kind = ?, workspace = ?, status = ?, capabilities_json = ?, last_seen = ?
                    WHERE id = ?
                    """,
                    (agent_kind, workspace_root, "online", _json_dumps(caps), now, row["id"]),
                )
                agent = Agent(
                    id=row["id"],
                    room_id=room.id,
                    name=agent_name,
                    kind=agent_kind,
                    workspace=workspace_root,
                    status="online",
                    capabilities=caps,
                    created_at=row["created_at"],
                    last_seen=now,
                )
                event = "agent.rejoined"
            else:
                agent = Agent(
                    id=make_id("agt"),
                    room_id=room.id,
                    name=agent_name,
                    kind=agent_kind,
                    workspace=workspace_root,
                    status="online",
                    capabilities=caps,
                    created_at=now,
                    last_seen=now,
                )
                conn.execute(
                    """
                    INSERT INTO agents(id, room_id, name, kind, workspace, status, capabilities_json, created_at, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        agent.id,
                        agent.room_id,
                        agent.name,
                        agent.kind,
                        agent.workspace,
                        agent.status,
                        _json_dumps(agent.capabilities),
                        agent.created_at,
                        agent.last_seen,
                    ),
                )
                event = "agent.joined"
            self.store.record_event(conn, "agent", agent.id, event, agent.name, asdict(agent))
            thread = self.store.ensure_thread(conn, room.id, "main")
            discovery = None
            if announce_discovery:
                discovery = self._maybe_insert_discovery(conn, room, thread, agent)
            result = {"room": asdict(room), "agent": asdict(agent), "default_thread": asdict(thread)}
            if discovery:
                result["discovery"] = asdict(discovery)
            return result

    def peers(self, room_name: str) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            rows = conn.execute(
                "SELECT * FROM agents WHERE room_id = ? ORDER BY name",
                (room.id,),
            ).fetchall()
            return [asdict(self.store._agent_from_row(row)) for row in rows]

    def status(self, room_name: str, agent_name: str | None = None, inbox_limit: int = 20) -> dict[str, Any]:
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            peer_rows = conn.execute(
                "SELECT * FROM agents WHERE room_id = ? ORDER BY name",
                (room.id,),
            ).fetchall()
            thread_rows = conn.execute(
                "SELECT * FROM threads WHERE room_id = ? ORDER BY updated_at DESC",
                (room.id,),
            ).fetchall()
            claim_rows = conn.execute(
                "SELECT * FROM scope_claims WHERE room_id = ? AND status = 'active' AND expires_at > ? ORDER BY created_at DESC",
                (room.id, utc_now()),
            ).fetchall()
            inbox = []
            if agent_name:
                self._require_agent(conn, room.id, agent_name)
                inbox = self.inbox(agent_name, room_name, include_resolved=False, include_seen=True, limit=inbox_limit)
            return {
                "db_path": str(self.store.db_path),
                "room": asdict(room),
                "agent": agent_name,
                "peers": [asdict(self.store._agent_from_row(row)) for row in peer_rows],
                "threads": [asdict(self.store._thread_from_row(row)) for row in thread_rows],
                "active_claims": [asdict(self.store._claim_from_row(row)) for row in claim_rows],
                "inbox": inbox,
            }

    def set_room_status(self, room_name: str, status: str, actor: str) -> dict[str, Any]:
        if status not in {"open", "paused", "closed"}:
            raise AgentMailError("room status must be one of: open, paused, closed")
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            self._require_agent(conn, room.id, actor)
            now = utc_now()
            conn.execute(
                "UPDATE rooms SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, room.id),
            )
            self.store.record_event(
                conn,
                "room",
                room.id,
                f"room.{status}",
                actor,
                {"previous_status": room.status, "status": status},
            )
            updated = self._require_room(conn, room_name)
            return {"room": asdict(updated)}

    def send(
        self,
        from_agent: str,
        to_agents: list[str],
        room_name: str,
        thread_title: str,
        subject: str,
        body: str,
        refs: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
        expects_reply: bool = True,
        parent_message_id: str = "",
    ) -> dict[str, Any]:
        if not to_agents:
            raise AgentMailError("at least one recipient is required")
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            if room.status != "open":
                raise AgentMailError(f"room '{room_name}' is {room.status}; reopen it before sending messages")
            self._require_agent(conn, room.id, from_agent)
            for recipient in to_agents:
                if recipient != "*":
                    self._require_agent(conn, room.id, recipient)
            thread = self.store.ensure_thread(conn, room.id, thread_title or "main")
            now = utc_now()
            trace_id = parent_message_id or make_id("trace")
            message = Message(
                id=make_id("msg"),
                room_id=room.id,
                thread_id=thread.id,
                parent_message_id=parent_message_id,
                from_agent=from_agent,
                to_agents=to_agents,
                subject=subject.strip() or "(no subject)",
                body=body,
                tags=tags or [],
                refs=refs or [],
                status="queued",
                expects_reply=expects_reply,
                trace_id=trace_id,
                created_at=now,
                updated_at=now,
            )
            self._insert_message(conn, message)
            self.store.record_event(conn, "message", message.id, "message.sent", from_agent, asdict(message))
            return {"message": asdict(message), "thread": asdict(thread), "room": asdict(room)}

    def inbox(
        self,
        agent_name: str,
        room_name: str,
        include_resolved: bool = False,
        include_seen: bool = True,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            self._require_agent(conn, room.id, agent_name)
            target = max(limit, 1)
            chunk_size = max(target * 5, 100)
            filtered = []
            cursor_created_at = ""
            cursor_id = ""
            while len(filtered) < target:
                params: list[Any] = [room.id]
                clauses = ["room_id = ?"]
                if not include_resolved:
                    clauses.append("status NOT IN ('resolved', 'cancelled', 'expired')")
                if not include_seen:
                    clauses.append("status IN ('queued', 'delivered')")
                if cursor_created_at:
                    clauses.append("(created_at < ? OR (created_at = ? AND id < ?))")
                    params.extend([cursor_created_at, cursor_created_at, cursor_id])
                params.append(chunk_size)
                rows = conn.execute(
                    f"""
                    SELECT * FROM messages
                    WHERE {' AND '.join(clauses)}
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    params,
                ).fetchall()
                if not rows:
                    break
                for row in rows:
                    message = self.store._message_from_row(row)
                    if agent_name not in message.to_agents and "*" not in message.to_agents:
                        continue
                    if message.from_agent == agent_name and "*" in message.to_agents and agent_name not in message.to_agents:
                        continue
                    filtered.append(asdict(message))
                    if len(filtered) >= target:
                        break
                cursor_created_at = rows[-1]["created_at"]
                cursor_id = rows[-1]["id"]
            return filtered[:target]

    def read_thread(self, room_name: str, thread: str = "main") -> dict[str, Any]:
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            thread_row = conn.execute(
                "SELECT * FROM threads WHERE room_id = ? AND (title = ? OR id = ?)",
                (room.id, thread, thread),
            ).fetchone()
            if not thread_row:
                raise NotFoundError(f"thread not found: {thread}")
            thread_obj = self.store._thread_from_row(thread_row)
            rows = conn.execute(
                "SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at ASC, id ASC",
                (thread_obj.id,),
            ).fetchall()
            return {
                "room": asdict(room),
                "thread": asdict(thread_obj),
                "messages": [asdict(self.store._message_from_row(row)) for row in rows],
            }

    def mark(self, message_id: str, status: str, actor: str) -> dict[str, Any]:
        if status not in VALID_MESSAGE_STATUSES:
            valid = ", ".join(sorted(VALID_MESSAGE_STATUSES))
            raise AgentMailError(f"invalid message status '{status}'. Expected one of: {valid}")
        with self.store.connect() as conn:
            message = self.store.find_message(conn, message_id)
            if not message:
                raise NotFoundError(f"message not found: {message_id}")
            self._require_agent(conn, message.room_id, actor)
            now = utc_now()
            conn.execute(
                "UPDATE messages SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, message_id),
            )
            self.store.record_event(
                conn,
                "message",
                message_id,
                f"message.{status}",
                actor,
                {"previous_status": message.status, "status": status},
            )
            updated = self.store.find_message(conn, message_id)
            return {"message": asdict(updated)}

    def reply(
        self,
        message_id: str,
        from_agent: str,
        body: str,
        refs: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
        resolve_original: bool = False,
    ) -> dict[str, Any]:
        with self.store.connect() as conn:
            original = self.store.find_message(conn, message_id)
            if not original:
                raise NotFoundError(f"message not found: {message_id}")
            room_row = conn.execute("SELECT * FROM rooms WHERE id = ?", (original.room_id,)).fetchone()
            if not room_row:
                raise NotFoundError("room not found for original message")
            room = self.store._room_from_row(room_row)
            if room.status != "open":
                raise AgentMailError(f"room '{room.name}' is {room.status}; reopen it before replying")
            self._require_agent(conn, original.room_id, from_agent)
            subject = f"Re: {original.subject}" if not original.subject.startswith("Re:") else original.subject
            now = utc_now()
            reply = Message(
                id=make_id("msg"),
                room_id=original.room_id,
                thread_id=original.thread_id,
                parent_message_id=original.id,
                from_agent=from_agent,
                to_agents=[original.from_agent],
                subject=subject,
                body=body,
                tags=tags or [],
                refs=refs or [],
                status="queued",
                expects_reply=False,
                trace_id=original.trace_id or original.id,
                created_at=now,
                updated_at=now,
            )
            self._insert_message(conn, reply)
            original_status = "resolved" if resolve_original else "replied"
            conn.execute(
                "UPDATE messages SET status = ?, updated_at = ? WHERE id = ?",
                (original_status, now, original.id),
            )
            self.store.record_event(conn, "message", reply.id, "message.replied", from_agent, asdict(reply))
            self.store.record_event(
                conn,
                "message",
                original.id,
                f"message.{original_status}",
                from_agent,
                {"reply_id": reply.id},
            )
            thread_row = conn.execute("SELECT * FROM threads WHERE id = ?", (original.thread_id,)).fetchone()
            return {
                "message": asdict(reply),
                "thread": asdict(self.store._thread_from_row(thread_row)),
                "room": asdict(room),
            }

    def note(
        self,
        from_agent: str,
        room_name: str,
        thread_title: str,
        body: str,
        refs: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.send(
            from_agent=from_agent,
            to_agents=["*"],
            room_name=room_name,
            thread_title=thread_title,
            subject="Shared note",
            body=body,
            refs=refs,
            tags=tags or ["note"],
            expects_reply=False,
        )

    def add_artifact(
        self,
        room_name: str,
        thread_title: str,
        created_by: str,
        artifact_type: str,
        path: str,
        summary: str = "",
    ) -> dict[str, Any]:
        if not path.strip():
            raise AgentMailError("artifact path is required")
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            self._require_agent(conn, room.id, created_by)
            thread = self.store.ensure_thread(conn, room.id, thread_title or "main")
            artifact = Artifact(
                id=make_id("art"),
                room_id=room.id,
                thread_id=thread.id,
                type=artifact_type.strip() or "file",
                path=path.strip(),
                summary=summary.strip(),
                created_by=created_by,
                created_at=utc_now(),
            )
            conn.execute(
                """
                INSERT INTO artifacts(id, room_id, thread_id, type, path, summary, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.id,
                    artifact.room_id,
                    artifact.thread_id,
                    artifact.type,
                    artifact.path,
                    artifact.summary,
                    artifact.created_by,
                    artifact.created_at,
                ),
            )
            self.store.record_event(conn, "artifact", artifact.id, "artifact.added", created_by, asdict(artifact))
            return {"artifact": asdict(artifact), "thread": asdict(thread), "room": asdict(room)}

    def artifacts(self, room_name: str, thread: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            params: list[Any] = [room.id]
            where = "WHERE room_id = ?"
            if thread:
                thread_row = conn.execute(
                    "SELECT * FROM threads WHERE room_id = ? AND (title = ? OR id = ?)",
                    (room.id, thread, thread),
                ).fetchone()
                if not thread_row:
                    raise NotFoundError(f"thread not found: {thread}")
                where += " AND thread_id = ?"
                params.append(thread_row["id"])
            params.append(max(limit, 1))
            rows = conn.execute(
                f"SELECT * FROM artifacts {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [asdict(self.store._artifact_from_row(row)) for row in rows]

    def claim_scope(
        self,
        agent_name: str,
        room_name: str,
        paths: list[str],
        reason: str,
        ttl_seconds: int = 3600,
        force: bool = False,
    ) -> dict[str, Any]:
        clean_paths = sorted({path.strip() for path in paths if path.strip()})
        if not clean_paths:
            raise AgentMailError("at least one path is required")
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            agent = self._require_agent(conn, room.id, agent_name)
            conflicts = self._scope_conflicts(conn, room.id, agent.id, clean_paths)
            if conflicts and not force:
                raise ConflictError("scope conflict: " + json.dumps(conflicts, ensure_ascii=False))
            now = utc_now()
            claim = ScopeClaim(
                id=make_id("claim"),
                room_id=room.id,
                agent_id=agent.id,
                paths=clean_paths,
                reason=reason.strip() or "No reason provided",
                status="active",
                expires_at=self.store.ttl_deadline(ttl_seconds),
                created_at=now,
                updated_at=now,
            )
            conn.execute(
                """
                INSERT INTO scope_claims(id, room_id, agent_id, paths_json, reason, status, expires_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.id,
                    claim.room_id,
                    claim.agent_id,
                    _json_dumps(claim.paths),
                    claim.reason,
                    claim.status,
                    claim.expires_at,
                    claim.created_at,
                    claim.updated_at,
                ),
            )
            self.store.record_event(conn, "scope_claim", claim.id, "scope.claimed", agent.name, asdict(claim))
            return {"claim": asdict(claim), "conflicts_overridden": conflicts}

    def release_scope(self, agent_name: str, room_name: str, paths: list[str] | None = None) -> dict[str, Any]:
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            agent = self._require_agent(conn, room.id, agent_name)
            rows = conn.execute(
                "SELECT * FROM scope_claims WHERE room_id = ? AND agent_id = ? AND status = 'active'",
                (room.id, agent.id),
            ).fetchall()
            wanted = sorted({path.strip() for path in (paths or []) if path.strip()})
            released = []
            now = utc_now()
            for row in rows:
                claim = self.store._claim_from_row(row)
                if wanted and not any(path in claim.paths for path in wanted):
                    continue
                conn.execute(
                    "UPDATE scope_claims SET status = 'released', updated_at = ? WHERE id = ?",
                    (now, claim.id),
                )
                released.append(asdict(claim))
                self.store.record_event(conn, "scope_claim", claim.id, "scope.released", agent.name, asdict(claim))
            return {"released": released}

    def timeline(self, room_name: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            room = self._require_room(conn, room_name)
            rows = conn.execute(
                """
                SELECT * FROM events
                WHERE entity_id IN (
                    SELECT id FROM messages WHERE room_id = ?
                    UNION SELECT id FROM threads WHERE room_id = ?
                    UNION SELECT id FROM scope_claims WHERE room_id = ?
                    UNION SELECT id FROM artifacts WHERE room_id = ?
                    UNION SELECT id FROM agents WHERE room_id = ?
                    UNION SELECT id FROM rooms WHERE id = ?
                )
                ORDER BY seq DESC LIMIT ?
                """,
                (room.id, room.id, room.id, room.id, room.id, room.id, max(limit, 1)),
            ).fetchall()
            return [
                {
                    "seq": row["seq"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "event_type": row["event_type"],
                    "actor": row["actor"],
                    "data": json.loads(row["data_json"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def _require_room(self, conn: Any, room_name: str) -> Room:
        room = self.store.find_room(conn, room_name)
        if not room:
            raise NotFoundError(f"room not found: {room_name}. Run agentmail join first.")
        return room

    def _require_agent(self, conn: Any, room_id: str, agent_name: str) -> Agent:
        row = conn.execute(
            "SELECT * FROM agents WHERE room_id = ? AND name = ?",
            (room_id, agent_name),
        ).fetchone()
        if not row:
            raise NotFoundError(f"agent not found in room: {agent_name}. Run agentmail join first.")
        return self.store._agent_from_row(row)

    def _insert_message(self, conn: Any, message: Message) -> None:
        conn.execute(
            """
            INSERT INTO messages(
                id, room_id, thread_id, parent_message_id, from_agent, to_agents_json,
                subject, body, tags_json, refs_json, status, expects_reply, trace_id,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.id,
                message.room_id,
                message.thread_id,
                message.parent_message_id,
                message.from_agent,
                _json_dumps(message.to_agents),
                message.subject,
                message.body,
                _json_dumps(message.tags),
                _json_dumps(message.refs),
                message.status,
                int(message.expects_reply),
                message.trace_id,
                message.created_at,
                message.updated_at,
            ),
        )

    def _maybe_insert_discovery(self, conn: Any, room: Room, thread: Thread, agent: Agent) -> Message | None:
        if room.status != "open":
            return None
        recipient_rows = conn.execute(
            "SELECT * FROM agents WHERE room_id = ? AND name != ? AND status = 'online' ORDER BY name",
            (room.id, agent.name),
        ).fetchall()
        recipients = [self.store._agent_from_row(row).name for row in recipient_rows]
        if not recipients:
            return None
        cutoff = (datetime.utcnow() - timedelta(seconds=DISCOVERY_DEDUP_SECONDS)).isoformat(timespec="microseconds") + "Z"
        recent = conn.execute(
            """
            SELECT id FROM messages
            WHERE room_id = ? AND from_agent = ? AND created_at >= ? AND tags_json LIKE ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (room.id, agent.name, cutoff, f'%"{DISCOVERY_TAG}"%'),
        ).fetchone()
        if recent:
            return None
        capabilities = ", ".join(agent.capabilities) if agent.capabilities else "(none)"
        body = "\n".join(
            [
                "AgentMail discovery notice.",
                "",
                f"Agent `{agent.name}` joined room `{room.name}`.",
                f"Kind: {agent.kind}",
                f"Workspace: {agent.workspace}",
                f"Capabilities: {capabilities}",
            ]
        )
        now = utc_now()
        message = Message(
            id=make_id("msg"),
            room_id=room.id,
            thread_id=thread.id,
            from_agent=agent.name,
            to_agents=recipients,
            subject=f"AgentMail discovery: {agent.name} joined {room.name}",
            body=body,
            tags=[DISCOVERY_TAG, "presence"],
            refs=[],
            status="queued",
            expects_reply=False,
            trace_id=make_id("trace"),
            created_at=now,
            updated_at=now,
        )
        self._insert_message(conn, message)
        self.store.record_event(conn, "message", message.id, "message.discovery", agent.name, asdict(message))
        return message

    def _scope_conflicts(
        self,
        conn: Any,
        room_id: str,
        agent_id: str,
        paths: list[str],
    ) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM scope_claims WHERE room_id = ? AND status = 'active' AND expires_at > ?",
            (room_id, utc_now()),
        ).fetchall()
        conflicts = []
        for row in rows:
            claim = self.store._claim_from_row(row)
            if claim.agent_id == agent_id:
                continue
            overlap = sorted(
                candidate
                for candidate in paths
                if any(_paths_overlap(candidate, claimed_path) for claimed_path in claim.paths)
            )
            if overlap:
                conflicts.append({"claim_id": claim.id, "agent_id": claim.agent_id, "paths": overlap})
        return conflicts


def _normalize_claim_path(path: str) -> str:
    normalized = str(Path(path).expanduser())
    return normalized.rstrip("/")


def _paths_overlap(left: str, right: str) -> bool:
    left_norm = _normalize_claim_path(left)
    right_norm = _normalize_claim_path(right)
    if left_norm == right_norm:
        return True
    return left_norm.startswith(right_norm + "/") or right_norm.startswith(left_norm + "/")
