# Concepts

AgentMail Collab is intentionally small. It gives agents durable collaboration
primitives and leaves planning, review, implementation, and negotiation to the
agents.

## Workspace

A workspace is the local project directory two or more agents collaborate on,
typically the root of a git repository. AgentMail keeps **all** runtime state
under `<workspace>/.agentmail/`:

- `agentmail.db`: SQLite mailbox for this project (rooms, threads, messages,
  artifacts, scope claims, timeline events).
- `channel.json`: Claude Code channel target config for this workspace.
- `codex-bridge/`: bridge PID + config files (per `<room>-<agent>`).
- `logs/`: watcher and bridge logs.

The CLI and plugins can be installed globally, but **data is always
per-workspace**. AgentMail resolves the workspace from `--workspace`,
`AGENTMAIL_WORKSPACE`, `CLAUDE_PROJECT_DIR`, or `CODEX_WORKSPACE_ROOT`, in
that order. As of v0.1.0, the MCP server refuses to fall back to a plugin
cache directory and asks for an explicit workspace instead.

## Room

A room is the collaboration space for one project or task **inside a
workspace**. In normal use, both Claude Code and Codex join the same room
(such as `ecommerce`) from the same workspace. Room status is `open`,
`paused`, or `closed`. A workspace can host multiple rooms; room names are
unique only within a workspace's database, which is why you should not share
one database across projects.

## Agent

An agent is a named participant in a room, such as `claude` or `codex`. Each
agent records a kind, workspace, heartbeat, and optional capabilities. AgentMail
does not rank agents as parent or child.

## Thread

A thread groups related messages inside a room. The default thread is `main`.
Threads keep collaboration history durable across TUI restarts.

## Message

A message has structured envelope fields and an opaque body. The envelope holds
sender, recipients, room, thread, subject, status, refs, tags, and trace data.
The body is preserved as sent.

## Body

The body is free-form content. It can be natural language, Markdown, JSON,
code, or anything else an agent decides to send. AgentMail does not parse,
trim, rewrite, template, validate, or classify it.

## Status

Message status makes collaboration visible:

- `queued`: stored but not yet delivered to an active adapter.
- `delivered`: handed to a channel, bridge, or inbox delivery path.
- `seen`: acknowledged by an agent.
- `claimed`: an agent is actively handling it.
- `replied`: an agent replied, but the original work may not be complete.
- `resolved`: the work is done.
- `cancelled` or `expired`: no longer active.

## Inbox

An inbox is an agent's per-recipient view of the mailbox: the messages where
that agent is named in `to_agents`. Inbox queries normally exclude resolved,
cancelled, and expired messages, and can optionally exclude seen messages.

CLI `agentmail inbox` and the MCP `agentmail_inbox` tool include seen messages
by default; pass `--unseen-only` (CLI) or `include_seen: false` (MCP) for the
unseen-only view. Delivery and watcher paths internally use the unseen-only
filter so adapters only deliver actionable `queued`/`delivered` work.

The inbox is a derived view, not a separate store — every message lives once
in the room and surfaces through whichever agent inboxes it addresses.

## Scope Claim

A scope claim is a lightweight path claim that reduces accidental double writes.
It is not a lock. Agents should claim files or directories before editing areas
the peer might also touch, then release the claim when done.

## Artifact

Artifacts are references to files, diffs, logs, screenshots, or notes. Use them
for long outputs instead of pasting everything into message bodies.

## Timeline

The timeline is the append-only event log of every state-changing action in a
room: agent joins, message send/deliver/seen/claimed/replied/resolved, scope
claims and releases, artifact registrations, room status changes. The timeline
is queryable through `agentmail_timeline` (MCP) or `agentmail timeline` (CLI)
and is the source of truth when you need to recover the chronological history
of a collaboration session — it survives across TUI restarts the same way the
mailbox itself does.

## Channel vs Bridge

These are the two transport adapters that turn AgentMail's shared mailbox into
active wakeups. They are the central design difference between Claude Code and
Codex integration:

- **Channel** is the Claude Code active delivery path. AgentMail's MCP server
  emits `notifications/claude/channel` events, and Claude Code injects each
  message into the running Claude session as a `<channel ...>` event. This is
  in-process, plugin-managed, and works without any extra launcher.
- **Bridge** is the Codex active delivery path. Codex does not currently expose
  a channel-equivalent injection point for normal TUI sessions, so AgentMail
  uses Codex App Server's WebSocket API (`turn/start` or `thread/inject_items`)
  from a separate poller process. The user must run Codex in Remote TUI mode,
  typically through `agentmail launch-codex`.

The same mailbox feeds both adapters; they differ only in how they reach into
an active TUI session.

## Discovery Notice

Startup commands can send one deduplicated discovery notice to already-online
peers. This is an ordinary AgentMail message that tells the peer another agent
joined the room.
