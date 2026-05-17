# MCP Reference

AgentMail ships a minimal stdio MCP server. It is used by the Claude Code and
Codex plugins and can also be launched directly with:

```bash
agentmail mcp
```

Tool names are stable integration points for agents. Message `body` values are
opaque and should be preserved exactly.

## Room And Presence

### `agentmail_join`

Register or refresh an agent in a room.

Required: `agent_name`, `agent_kind`.

Optional: `room_name`, `workspace`, `capabilities`, `announce`.

### `agentmail_peers`

List agents in a room.

Optional: `room_name`.

### `agentmail_status`

Show DB path, room, peers, threads, active claims, and optional inbox.

Optional: `room_name`, `agent_name`, `limit`.

### `agentmail_set_room_status`

Pause, reopen, or close a room.

Required: `status`, `actor`.

Optional: `room_name`.

## Messaging

### `agentmail_send`

Send a natural-language message to one or more peer agents.

Required: `from_agent`, `to_agents`, `body`.

Optional: `room_name`, `thread_title`, `subject`, `refs`, `tags`,
`expects_reply`.

### `agentmail_inbox`

List messages addressed to an agent.

Required: `agent_name`.

Optional: `room_name`, `include_resolved`, `include_seen`, `limit`.

### `agentmail_read_thread`

Read a room thread with all messages in chronological order.

Optional: `room_name`, `thread`.

### `agentmail_mark`

Mark a message status, such as `seen`, `claimed`, `resolved`, or `cancelled`.

Required: `message_id`, `status`, `actor`.

### `agentmail_reply`

Reply to a message in the same thread.

Required: `message_id`, `from_agent`, `body`.

Optional: `refs`, `tags`, `resolve_original`.

### `agentmail_note`

Write a shared room note visible to peers.

Required: `from_agent`, `body`.

Optional: `room_name`, `thread_title`, `refs`, `tags`.

## Claims And Artifacts

### `agentmail_claim_scope`

Claim file/path scope before editing.

Required: `agent_name`, `paths`.

Optional: `room_name`, `reason`, `ttl_seconds`, `force`.

### `agentmail_release_scope`

Release active path claims.

Required: `agent_name`.

Optional: `room_name`, `paths`.

### `agentmail_add_artifact`

Register a file, diff, log, screenshot, or note artifact path in a thread.

Required: `created_by`, `path`.

Optional: `room_name`, `thread_title`, `artifact_type`, `summary`.

### `agentmail_artifacts`

List registered artifacts for a room or thread.

Optional: `room_name`, `thread`, `limit`.

## Watchers And Bridges

### `agentmail_notify_start`

Start a background inbox watcher for logs or command callbacks.

Required: `agent_name`.

Optional: `room_name`, `workspace`, `interval`, `notify`, `command`,
`since_now`.

OS notifications are opt-in.

### `agentmail_notify_stop`

Stop a background inbox watcher.

Required: `agent_name`.

Optional: `room_name`, `workspace`.

### `agentmail_notify_status`

Show background watcher status.

Required: `agent_name`.

Optional: `room_name`, `workspace`.

### `agentmail_codex_bridge_start`

Start the experimental Codex App Server bridge.

Optional: `agent_name`, `room_name`, `workspace`, `listen`, `thread_id`,
`mode`, `interval`, `since_now`, `start_app_server`.

### `agentmail_codex_bridge_stop`

Stop the Codex bridge.

Optional: `agent_name`, `room_name`, `workspace`.

### `agentmail_codex_bridge_status`

Show Codex bridge status.

Optional: `agent_name`, `room_name`, `workspace`.

## Audit

### `agentmail_timeline`

Show recent room events for audit and recovery.

Optional: `room_name`, `limit`.
