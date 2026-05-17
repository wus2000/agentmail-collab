# AgentMail

AgentMail is a local peer-to-peer mailbox for coding agents such as Claude Code
and Codex. It is intentionally a thin collaboration layer: agents decide how to
plan, review, implement, and negotiate in natural language; AgentMail only
provides reliable messaging, status, shared thread history, artifacts, and
file-scope claims.

AgentMail treats message `body` as an opaque payload. Apart from small envelope
fields such as sender, recipients, room, thread, status, refs, and tags, it does
not parse, trim, rewrite, template, validate, or classify message content. What
an agent sends in `body` is what the peer receives. For exact multi-line content
over the CLI, prefer `--body-file` or stdin.

## Goals

- Let Claude Code and Codex run side by side in the same codebase.
- Keep both agents as peers, not as parent/child tools.
- Persist messages and state across TUI restarts.
- Push inbox messages into a running Claude Code session through Claude channels.
- Experimentally push Claude-origin inbox messages into a Codex Remote TUI
  session through Codex App Server.
- Show whether a message was delivered, seen, claimed, replied to, or resolved.
- Allow agents to reference files, diffs, logs, screenshots, and notes.
- Register artifacts as first-class thread objects.
- Reduce accidental double writes with lightweight path claims.
- Pause, reopen, or close a room without deleting history.
- Keep the core workflow-free and extensible through adapters.

## Non-Goals

- AgentMail does not decide who plans, implements, or reviews.
- AgentMail does not execute shell commands from messages.
- AgentMail does not require Claude or Codex to be subordinate to each other.
- AgentMail does not depend on this repository's existing teammate scripts.

## Layout

```text
agentmail/
  .claude-plugin/marketplace.json  Claude Code marketplace entrypoint
  .agents/plugins/marketplace.json Codex marketplace entrypoint
  pyproject.toml   Python package metadata
  models.py       Generic domain models
  store.py        SQLite persistence and event log
  service.py      Workflow-free application API
  cli.py          `agentmail ...`
  codex_bridge.py Experimental Codex App Server bridge
  daemon.py       Local JSON RPC daemon
  mcp_server.py   Minimal stdio MCP server and Claude channel
  notify.py       Background watcher and channel config helpers
  skills/         Claude/Codex usage instructions
  plugins/        Codex and Claude Code local plugin marketplaces
  docs/           Install, test, and release guides
  scripts/        Validation and local install helpers
  tests/          Unit and integration tests
```

## Install As Plugins

AgentMail is packaged so this `agentmail/` directory can be used as the
marketplace root for both Claude Code and Codex.

Install the CLI command first:

```bash
cd agentmail
python3 -m pip install -e .
agentmail --help
```

The docs use `agentmail ...` for normal usage. When hacking directly on the
source tree before installing the CLI, `python -m agentmail ...` remains an
equivalent fallback.

Claude Code:

```bash
claude plugin validate .
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-local --scope local
```

For Claude channel wakeups, start Claude Code with the development-channel
bypass while channels are in research preview:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-local
```

Then join a room inside Claude Code:

```text
/agentmail:start ecommerce claude
```

Codex:

```bash
cd agentmail
codex plugin marketplace add "$(pwd)"
```

Restart Codex, install `agentmail` from the `AgentMail Local` marketplace, then
join the same room:

```text
Use @agentmail. Join room ecommerce as codex, list peers, and check my inbox.
```

See `docs/INSTALL.md` for the full install and smoke-test flow.

## Active Wakeups

AgentMail has one mailbox and two wakeup adapters:

- **Claude Code**: the AgentMail MCP server emits
  `notifications/claude/channel`, and Claude Code injects the message into the
  running Claude session. This is the primary Claude wakeup path.
- **Codex**: the experimental bridge connects to Codex App Server and delivers
  new AgentMail inbox messages with `turn/start` or `thread/inject_items`.
  This requires Codex to run through Remote TUI mode; a normal already-opened
  `codex` TUI cannot currently be injected through the plugin/MCP layer.

For the natural "start a collaboration-ready Codex" path, launch Codex through
AgentMail from the project directory:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

Resume the most recent Codex session through the same wakeup path:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

If you already opened a normal Codex TUI, ask it to run:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

To bootstrap into the most recent Codex session:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD" --resume last
```

`bootstrap-codex` prepares the workspace and opens a new AgentMail-aware Codex
Remote TUI window. Continue the collaboration in that new Codex window; the
original normal TUI still cannot be injected directly.

You can inspect the local setup at any time:

```bash
agentmail doctor --room ecommerce --workspace "$PWD"
```

Or run the pieces manually:

```bash
codex app-server --listen ws://127.0.0.1:4500
agentmail codex-bridge start \
  --agent codex \
  --room ecommerce \
  --workspace "$PWD" \
  --listen ws://127.0.0.1:4500 \
  --no-app-server
codex --remote ws://127.0.0.1:4500
```

If more than one Codex thread is loaded, pass `--thread-id` so AgentMail knows
which thread to wake. Use `--mode inject` only when you want to add context
without starting a new Codex turn. The default `turn-start` mode consumes Codex
API budget per delivered message; `inject` only seeds context and does not run
the model by itself.

## Quick Start

From a repository where both agents are working:

```bash
agentmail start --agent claude --kind claude --room ecommerce
agentmail start --agent codex --kind codex --room ecommerce
agentmail peers --room ecommerce
agentmail status --agent codex --room ecommerce
```

Send a message from Codex to Claude:

```bash
agentmail send \
  --from codex \
  --to claude \
  --room ecommerce \
  --thread main \
  --subject "Architecture help" \
  --body "User wants us to build an ecommerce management system. Please reason about module boundaries and risks."
```

Read and reply from Claude:

```bash
agentmail inbox --agent claude --room ecommerce
agentmail mark --agent claude --message msg_xxx --status claimed
agentmail reply --agent claude --message msg_xxx --body "I will focus on architecture and data consistency risks."
```

Claim files before editing:

```bash
agentmail claim-scope \
  --agent codex \
  --room ecommerce \
  --path src/orders \
  --reason "Implementing order workflow slice"
```

Register an artifact:

```bash
agentmail artifact-add \
  --agent codex \
  --room ecommerce \
  --type log \
  --path .agentmail/artifacts/test.log \
  --summary "Focused test output"
```

Pause a room:

```bash
agentmail room-status --agent claude --room ecommerce --status paused
```

Start a background watcher for future inbox messages. It logs new messages and
can run a command callback; OS notifications are off by default.

```bash
agentmail notify-start --agent claude --room ecommerce --workspace "$PWD"
agentmail notify-status --agent claude --room ecommerce --workspace "$PWD"
agentmail notify-stop --agent claude --room ecommerce --workspace "$PWD"
```

If you explicitly want an OS notification fallback, opt in:

```bash
agentmail notify-start --agent claude --room ecommerce --workspace "$PWD" --os-notify
```

Configure Claude channel delivery for a room:

```bash
agentmail channel-config --agent claude --room ecommerce --workspace "$PWD"
agentmail channel-status --workspace "$PWD"
```

When the Claude plugin MCP server is launched with channel support, new inbox
messages for that room are emitted as `notifications/claude/channel`. Claude
Code wraps them as `<channel source="agentmail" ...>` events in the running
session. The event body is exactly the AgentMail message body; routing metadata
is carried as tag attributes.

## Local Daemon

The daemon exposes a tiny JSON RPC endpoint for adapters:

```bash
agentmail serve --host 127.0.0.1 --port 8765
```

Health checks:

```bash
curl http://127.0.0.1:8765/healthz
```

RPC shape:

```json
{
  "method": "inbox",
  "params": {
    "agent_name": "claude",
    "room_name": "ecommerce"
  }
}
```

## MCP

Run the stdio MCP server:

```bash
agentmail mcp
```

For Claude channel mode, set `AGENTMAIL_CHANNEL=1` in the MCP server
environment. The Claude plugin does this automatically.

Example MCP server command:

```json
{
  "mcpServers": {
    "agentmail": {
      "command": "python",
      "args": ["-m", "agentmail", "mcp"],
      "env": {
        "AGENTMAIL_DB": "/absolute/path/to/repo/.agentmail/agentmail.db"
      }
    }
  }
}
```

Tools exposed:

- `agentmail_join`
- `agentmail_peers`
- `agentmail_status`
- `agentmail_set_room_status`
- `agentmail_send`
- `agentmail_inbox`
- `agentmail_read_thread`
- `agentmail_mark`
- `agentmail_reply`
- `agentmail_note`
- `agentmail_add_artifact`
- `agentmail_artifacts`
- `agentmail_claim_scope`
- `agentmail_release_scope`
- `agentmail_notify_start`
- `agentmail_notify_stop`
- `agentmail_notify_status`
- `agentmail_codex_bridge_start`
- `agentmail_codex_bridge_stop`
- `agentmail_codex_bridge_status`
- `agentmail_timeline`

## Plugins

Installable marketplace payloads live under `agentmail/plugins/`:

- `agentmail/plugins/claude-marketplace` for Claude Code.
- `agentmail/plugins/codex-marketplace` for Codex.

The repository root also exposes official marketplace entrypoints:

- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json`

See `plugins/README.md` for package internals.

## Agent Behavior Guidance

Agents should use AgentMail as a shared mailbox and memory, not as a rigid
workflow engine:

- Join the room before collaborating.
- Check peers before assuming the other agent is online.
- Put free-form communication in `body`; AgentMail will not rewrite it.
- Send short messages and attach long context as refs.
- Mark important messages as `seen` or `claimed` before working on them.
- Reply in the same thread when continuing a conversation.
- Register long logs, diffs, and generated files as artifacts.
- Claim paths before editing files that a peer may also touch.
- Release claims when done.
- Pause a room before major user redirection or when automation should stop.
- Ask the user when a high-risk decision is required.

## Verification

```bash
cd agentmail
./scripts/validate.sh
```
