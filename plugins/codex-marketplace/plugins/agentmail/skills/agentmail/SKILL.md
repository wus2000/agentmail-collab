---
name: agentmail
description: Use AgentMail any time Codex is asked to coordinate with a peer Claude Code or Codex session in the same workspace through the local mailbox. Triggers include sending/receiving peer messages, checking inbox, claiming file scope before editing, marking peer work seen/claimed/resolved, registering long outputs as artifacts, or any user mention of "Claude", "peer", "teammate", "the other agent", or "send a message". Also trigger when an independent review by the peer agent would improve correctness, architecture, scope, or review quality. Prefer the bundled MCP tools (`agentmail_*`) over shelling out. Do NOT use for solo work, chats with the user only, or when no peer is online.
---

# AgentMail

Use AgentMail as a peer mailbox, not as a workflow engine. The only structured
part is the envelope: sender, recipients, room, thread, status, refs, tags, and
artifact metadata. Message `body` is opaque and must be preserved exactly.

## When To Use

Trigger when the user mentions Claude, a peer agent, or a teammate session;
when sending/receiving messages between agents; before editing files another
agent may touch (scope claim); after producing long outputs (register as
artifact); or when the peer's independent judgment would improve correctness,
architecture, scope, or review quality.

Do NOT use when only the user is involved, no peer is online (check
`agentmail_peers`), or every small implementation step does not need peer
input — keep collaboration peer-level, not micromanaged.

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
- `agentmail_codex_bridge_start`, `agentmail_codex_bridge_status`, and
  `agentmail_codex_bridge_stop` for experimental Codex App Server active
  wakeups.

Startup pattern for Codex:

1. Join the requested room as `codex` with `agent_kind: codex`.
2. Always pass the current repository path as `workspace` on the first join.
   AgentMail uses that path to select `<workspace>/.agentmail/agentmail.db`
   for this MCP session.
   If this is a startup join rather than a quiet heartbeat, pass
   `announce: true` so online peers receive one deduplicated discovery message.
3. For ordinary Codex TUI sessions, read inbox explicitly. For active
   Claude-to-Codex wakeups, prefer
   `agentmail launch-codex --room <room> --workspace "$PWD"`.
   Use `--resume last` or `--resume <session-id>` when the user wants to resume
   a previous Codex conversation. The launcher forwards `AGENTMAIL_DB` and
   `AGENTMAIL_WORKSPACE` so MCP tools and the bridge share one database.
   If you are already inside a normal Codex TUI, use
   `agentmail bootstrap-codex --room <room> --workspace "$PWD"` to
   open a new AgentMail-aware Remote TUI.
4. List peers and read inbox before sending new work.
5. Send natural-language content in `body`; do not wrap it in a custom protocol.

If MCP tools are not loaded, tell the user to enable the AgentMail plugin or set
`AGENTMAIL_DB` before launching both TUIs.
