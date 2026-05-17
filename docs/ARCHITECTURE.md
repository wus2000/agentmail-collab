# Architecture

AgentMail Collab has one mailbox core and transport adapters around it.

```text
            Claude Code TUI                         Codex Remote TUI
                  |                                      |
      Claude channel notification              Codex App Server websocket
                  |                                      |
            mcp_server.py                         codex_bridge.py
                  |                                      |
                  +--------------+---------------+
                                 |
                           service.py
                                 |
                            store.py
                                 |
                    <workspace>/.agentmail/agentmail.db
```

## Design Principles

- AgentMail is a mailbox, not an orchestrator.
- AgentMail keeps Claude Code and Codex as peers; neither is master, neither
  is a tool of the other.
- Message bodies are opaque and exact. AgentMail does not parse, classify,
  rewrite, template, validate, or trim them.
- The structured protocol stays small: envelope, status, refs, tags, artifacts,
  and scope claims. Anything that can live in body, lives in body.
- Workflows live in agent conversation, not in hard-coded coordination logic.
- Two adapters, one mailbox: Claude Code uses MCP-emitted channel events;
  Codex uses an external bridge to App Server. Both read from the same
  `service.inbox(...)` and write the same `status` transitions.

## Deployment Posture

AgentMail Collab separates **tools** (install once, globally) from **data**
(per project, never globally exported).

```text
GLOBAL (install once)                         PER WORKSPACE (per project)
─────────────────────                         ──────────────────────────
~/.local/bin/agentmail                        <project>/.agentmail/
  (or wherever pip put it)                       ├── agentmail.db
                                                 ├── channel.json
~/.claude/plugins/.../agentmail/                 ├── codex-bridge/
  (user-scope plugin payload)                    │     <room>-<agent>.pid
  ├── .claude-plugin/plugin.json                 │     <room>-<agent>.json
  ├── .mcp.json                                  ├── logs/
  ├── bin/                                       │     <room>-<agent>.codex-bridge.log
  ├── commands/                                  │     <room>-<agent>.codex-app-server.log
  ├── skills/                                    └── watch/<room>-<agent>.pid
  └── vendor/agentmail/   ← Python runtime

~/.codex/plugins/.../agentmail/
  (personal Codex plugin payload, same shape)
```

Why the split:

- **Tools (CLI + plugin payloads + bundled Python runtime)** are static
  artifacts of a particular AgentMail version. They live in user-scope plugin
  caches or your `$PATH`. Reinstalling or upgrading replaces the tool but
  leaves project data alone.
- **Data (the SQLite mailbox, channel target, bridge state, logs)** is unique
  per project. Cross-project collaboration would mix unrelated rooms, threads,
  and file-scope claims into the same namespace, so AgentMail deliberately
  keeps each workspace isolated.

Two consequences flow from this:

1. **Do not globally export `AGENTMAIL_DB`.** It collapses all projects into
   one room namespace and is almost never what you want.
2. **MCP server refuses plugin-cache DB fallback** (v0.1.0+). If the MCP
   server cannot infer a workspace, it raises an explicit error instead of
   silently creating a database inside the plugin cache directory. Pass
   `workspace` on the first tool call, or set `AGENTMAIL_WORKSPACE` /
   `CODEX_WORKSPACE_ROOT` / `CLAUDE_PROJECT_DIR` in the environment.

The AgentMail-managed launchers (`agentmail launch-codex`,
`agentmail bootstrap-codex`) take `--workspace "$PWD"` and forward both
`AGENTMAIL_DB` and `AGENTMAIL_WORKSPACE` into the spawned Codex Remote TUI,
which is why they are the recommended Codex active-wakeup entry point.

## Core Mailbox

`service.py` exposes workflow-free application operations: join, send, inbox,
read thread, mark, reply, claim scope, release scope, add artifacts, inspect
timeline, and set room status.

`store.py` owns SQLite persistence, schema creation, row conversion, UTC
timestamps, IDs, and the append-only event timeline.

## Transport Adapters

Claude Code uses `mcp_server.py` plus Claude channels. When Claude joins a room,
AgentMail writes channel configuration under `.agentmail/`. The MCP server polls
the target inbox and emits `notifications/claude/channel` events into the active
Claude Code session.

Codex uses `codex_bridge.py` for active wakeups. The bridge connects to Codex
App Server and sends inbound messages through `turn/start` or
`thread/inject_items`. Because normal Codex plugin/MCP sessions cannot be
injected directly, active wakeups require Remote TUI mode.

## Plugins And Skills

The plugin packages connect Claude Code and Codex to the local mailbox through
MCP and bundled wrapper scripts. The skills teach agents when and how to use the
mailbox. In OpenAI terminology, the plugin provides tool/data access and the
skill provides repeatable process guidance.

AgentMail intentionally ships no plugin `agents/` directory. Agent behavior is
negotiated through message bodies rather than being packaged as a fixed
subagent persona.

## Components And Module Map

The codebase is intentionally small. Contributors usually only need this module
map before jumping into the files:

```text
Module             Role
models.py          Domain dataclasses
store.py           SQLite persistence, schema creation, IDs, timestamps, events
service.py         Workflow-free application API and domain validation
cli.py             argparse CLI surface and launch/bootstrap commands
mcp_server.py      stdio MCP tools and Claude channel delivery
notify.py          Watcher process management and channel config helpers
codex_bridge.py    Codex App Server bridge and Remote TUI delivery
daemon.py          Optional local JSON-RPC daemon
```

### Core Domain

- `models.py`: dataclasses for rooms, agents, threads, messages, artifacts, and
  scope claims. Pure data, no I/O.
- `store.py`: SQLite schema, migrations-on-open, row conversion, ID helpers,
  timestamp helpers, event recording, and default database path resolution.
- `service.py`: application-level operations and domain validation. This is
  the main API used by CLI, MCP, and adapters. Public flows such as join, send,
  mark, claim, artifact registration, channel config, and discovery notices
  live here instead of in surface layers.

### Interfaces And Packaging

- `cli.py`: `agentmail ...` command inventory, including mailbox operations,
  watchers, channel config, Codex launch/bootstrap, bridge management, doctor,
  daemon, and MCP server startup. See [CLI_REFERENCE.md](CLI_REFERENCE.md).
- `mcp_server.py`: stdio MCP server with AgentMail tools and Claude channel
  delivery when `AGENTMAIL_CHANNEL=1`. See
  [MCP_REFERENCE.md](MCP_REFERENCE.md).
- `notify.py`: watcher process management, command callbacks, OS notification
  opt-in, and channel config helpers.
- `codex_bridge.py`: Codex App Server client, bridge lifecycle, WebSocket
  framing, delivery modes, status files, and Remote TUI launch support. See
  [CODEX_BRIDGE.md](CODEX_BRIDGE.md).
- `daemon.py`: optional local JSON-RPC daemon for helper processes.

Plugin payloads live under `plugins/claude-marketplace/plugins/agentmail/` and
`plugins/codex-marketplace/plugins/agentmail/`. `plugins/sync_vendor.py` keeps
their vendored `vendor/agentmail/` runtime in sync with the source package so
installed plugins are self-contained.

## Data Flow

```text
   sender                    mailbox            adapter            receiver
   ──────                    ───────            ───────            ────────
   send ───── store.message ─→  queued
                                  │
                                  └─── inbox poll ──→ deliver ─→  delivered
                                                                    │
                                                          channel  │ bridge
                                                          event  ──┴── ws frame
                                                                    │
                                                                    ▼
                                                                   seen
                                                                    │
                                                                  claimed
                                                                    │
                                                                  replied
                                                                    │
                                                                  resolved
```

1. An agent joins a room (and optionally announces discovery to peers).
2. The peer sends a message through CLI or MCP.
3. The message is stored as `queued` in the same SQLite mailbox both adapters
   read from.
4. A delivery adapter (channel for Claude, bridge for Codex) sees the inbox
   item via the same `service.inbox(...)` filter.
5. The adapter delivers it (notification emit or WebSocket call) and marks it
   `delivered`.
6. The receiving agent marks it `seen` or `claimed`.
7. The receiving agent replies, resolves it, or registers artifacts.

Status is the end-to-end coordination signal. Delivery alone is not proof that
the receiving agent finished the work — only the receiver's status transitions
prove that.

## Extension Point

To support another agent runtime, add an adapter that:

1. Joins as a named agent in the shared room.
2. Polls or subscribes to that agent inbox.
3. Preserves the message body exactly when injecting it into the runtime.
4. Marks messages only after successful delivery.
5. Leaves workflow decisions to the receiving agent.
