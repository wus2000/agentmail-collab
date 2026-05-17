---
description: Use AgentMail when coordinating with a peer Codex or Claude Code session through a local mailbox.
---

# AgentMail

Use AgentMail as a peer mailbox, not as a workflow engine. The only structured
part is the envelope: sender, recipients, room, thread, status, refs, tags, and
artifact metadata. Message `body` is opaque and must be preserved exactly.

Prefer MCP tools when they are available:

- `agentmail_join` when entering or refreshing a room.
- `agentmail_peers` before assuming the other agent is online.
- `agentmail_status` to inspect DB path, peers, inbox, active claims, and room state.
- `agentmail_send` for free-form peer messages.
- `agentmail_inbox` to check work addressed to this agent.
- `agentmail_mark` with `seen`, `claimed`, `resolved`, or `cancelled`.
- `agentmail_reply` to continue an existing thread.
- `agentmail_note` for shared room notes.
- `agentmail_claim_scope` before editing paths the peer may touch.
- `agentmail_release_scope` when done.
- `agentmail_add_artifact` for files, diffs, logs, screenshots, and notes.
- `agentmail_timeline` when recovering context.
- `agentmail_notify_start` to start a background inbox watcher.
- `agentmail_notify_status` and `agentmail_notify_stop` to inspect or stop it.

Startup pattern for Claude Code:

1. Join the requested room as `claude` with `agent_kind: claude`.
2. Always pass `${CLAUDE_PROJECT_DIR}` as `workspace` when available.
   AgentMail uses that path to select `<workspace>/.agentmail/agentmail.db`
   for this MCP session.
   If this is a startup join rather than a quiet heartbeat, pass
   `announce: true` so online peers receive one deduplicated discovery message.
3. If Claude Code was launched with channels enabled for this plugin, AgentMail
   pushes future inbox messages into the running session as
   `<channel source="agentmail" ...>` events. The event body is the exact peer
   message body; use tag attributes such as `message_id` and `from_agent` for
   routing.
4. Start `agentmail_notify_start` for `claude` if the user wants OS
   notifications or command callbacks for new inbox messages.
5. List peers and read inbox before sending new work.
6. Send natural-language content in `body`; do not wrap it in a custom protocol.

Codex can only be actively woken when it was started through the experimental
AgentMail Codex App Server bridge. Otherwise, Codex must read its inbox on the
next turn. Prefer asking the user or Codex to start it with
`agentmail launch-codex --room <room> --workspace "$PWD"`; the launcher forwards
`AGENTMAIL_DB` and `AGENTMAIL_WORKSPACE` so Codex MCP tools and the bridge share
one database.

If MCP tools are not loaded, use the bundled CLI:

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/agentmail" --json start --agent claude --kind claude --room default --workspace "${CLAUDE_PROJECT_DIR:-$PWD}"
```
