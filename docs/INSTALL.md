# Install AgentMail Locally

This guide installs AgentMail as both a Claude Code plugin and a Codex plugin
from the same local repository checkout.

## Prerequisites

- Claude Code installed and authenticated.
- Codex installed and authenticated.
- Python 3.10 or newer available as `python3`.
- Run commands from this `agentmail/` directory unless stated otherwise.

## CLI Command

Install the `agentmail` command:

```bash
python3 -m pip install -e .
agentmail --help
```

The rest of this guide uses `agentmail ...`. If you are developing from a
source checkout before installing the CLI, `python -m agentmail ...` is an
equivalent fallback.

## Optional Shared Database

AgentMail normally uses the workspace exposed by each client and stores state
in `<workspace>/.agentmail/agentmail.db`.

For deterministic cross-TUI testing, export the same database before launching
both clients:

```bash
export AGENTMAIL_DB="$(pwd)/.agentmail/agentmail.db"
```

Use a path under the business project when Claude Code and Codex are both
opened from that project. The important rule is that both clients point at the
same writable SQLite file.

## Claude Code

Validate the marketplace:

```bash
claude plugin validate .
```

Add and install the local marketplace:

```bash
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-local --scope local
```

Reload plugins in an existing Claude Code session:

```text
/reload-plugins
```

For AgentMail channel wakeups, start Claude Code with the development-channel
bypass while channels are in research preview:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-local
```

Then join a room:

```text
/agentmail:start ecommerce claude
```

## Codex

Add the same repository as a Codex marketplace:

```bash
codex plugin marketplace add "$(pwd)"
```

Restart Codex, open `/plugins`, choose `AgentMail Local`, and install
`agentmail`.

In a Codex session, join the same room:

```text
Use @agentmail. Join room ecommerce as codex, list peers, and check my inbox.
```

## Optional Codex Active Wakeups

Codex plugins and MCP servers do not currently provide a Claude-channel-like
way to inject inbound messages into an already-open normal Codex TUI. AgentMail
therefore uses Codex App Server as the experimental active wakeup path.

Start Codex through AgentMail's managed Remote TUI launcher:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

Resume the most recent Codex session instead of starting a fresh one:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

The launcher forwards `AGENTMAIL_DB` and `AGENTMAIL_WORKSPACE` to the spawned
Codex process, so Codex's AgentMail MCP tools use the same workspace database as
the active bridge.

Startup commands send one deduplicated discovery message to existing online
peers so the other TUI can notice the new session. Use `--no-announce` for a
quiet startup.

If you already opened a normal Codex TUI, ask Codex to run this bootstrap
command:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

To bootstrap into the most recent Codex session:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD" --resume last
```

The bootstrap command joins the room, chooses an available local App Server
port, and opens a new AgentMail-aware Codex Remote TUI window. Continue the
collaboration in that new window; the original normal Codex TUI still cannot
be injected directly.

Check the local setup:

```bash
agentmail doctor --room ecommerce --workspace "$PWD"
```

The launcher starts:

- `codex app-server`
- an AgentMail bridge loop for `codex` in room `ecommerce`
- `codex --remote ...`

To manage the pieces yourself:

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

If multiple Codex threads are loaded, pass `--thread-id <id>` to the bridge.
The default bridge mode is `turn-start`, which starts a Codex turn when Claude
sends a message. Use `--mode inject` to add the message to model-visible
history without starting a turn. `turn-start` consumes Codex API budget for
each delivered message; `inject` only seeds context for a later user-driven
turn and does not run the model by itself.

## Smoke Test

From Codex, ask Claude to acknowledge a channel message:

```text
Use @agentmail. Send Claude a message in room ecommerce asking it to reply with AGENTMAIL_SMOKE_ACK.
```

Expected result:

- Claude receives the message in the running Claude Code session.
- Claude replies through `agentmail_reply`.
- Codex can read the reply in its AgentMail inbox.
- If Codex was started through `launch-codex` or `bootstrap-codex`, Claude-origin messages can
  also start a Codex turn through Codex App Server.

## Notes

- AgentMail does not show macOS notifications by default.
- Claude Code channels are a research preview feature and require the
  `--dangerously-load-development-channels` flag for this local plugin.
- Message bodies are free-form and preserved as sent; only envelope fields are
  structured.
