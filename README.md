# AgentMail Collab

**AgentMail Collab is a local peer mailbox, not an agent orchestrator.**

Other Claude/Codex bridges turn one CLI into a tool of the other. AgentMail
keeps both CLIs autonomous and lets them talk like peers through a shared local
SQLite mailbox: same workspace, same room, same thread, same opaque message
bodies, with Claude Code channels and a Codex App Server bridge as transport
adapters.

AgentMail Collab is unrelated to the hosted `agentmail` PyPI package. We ship as
`agentmail-collab` to avoid confusion.

[中文 README](README.zh-CN.md)

## What You Get

- A durable local mailbox for Claude Code, Codex, and other coding agents.
- Rooms, threads, message status, artifacts, event history, and file-scope
  claims backed by SQLite under your workspace.
- Claude Code active wakeups through Claude channels.
- Experimental Claude-to-Codex active wakeups through Codex App Server and
  Remote TUI mode.
- Plugin packages for both Claude Code and Codex, plus a normal `agentmail`
  CLI for scripting and local debugging.

Message bodies are opaque. AgentMail stores and delivers the body exactly as an
agent sends it; only envelope fields such as sender, recipients, room, thread,
status, refs, and tags are structured.

## Requirements

- Claude Code installed and authenticated.
- Codex installed and authenticated.
- Python 3.10 or newer.
- macOS or Linux for the best-tested local workflow. Windows users should use
  WSL for now.

## Compared To

- Compared to `openai/codex-plugin-cc`, AgentMail is peer-to-peer instead of
  delegation from Claude Code into Codex.
- Compared to one-way Claude/Codex config bridges, AgentMail persists actual
  messages, status, artifacts, and scope claims.
- Compared to network agent protocols such as A2A, AgentMail is local-first and
  deliberately light on protocol.
- Compared to the hosted `agentmail` PyPI package, AgentMail Collab is a separate
  local mailbox for coding-agent collaboration.

## Quick Start From Source

Install the AgentMail Collab CLI and plugin marketplaces once, then use them from any
project. The tooling can be global; collaboration state stays local to each
workspace under `<project>/.agentmail/`.

Clone the repository:

```bash
git clone https://github.com/wus2000/agentmail-collab agentmail-collab
cd agentmail-collab
```

Install the CLI from this checkout:

```bash
python3 -m pip install -e .
agentmail --help
```

Install the Claude Code plugin marketplace from the repository root. User scope
is the recommended long-term install because it is available across projects:

```bash
claude plugin validate .
claude plugin marketplace add "$(pwd)" --scope user
claude plugin install agentmail@agentmail-collab --scope user
```

Use `--scope local` instead when you want a one-project development install.

Install the Codex plugin marketplace from the same repository root:

```bash
codex plugin marketplace add "$(pwd)"
```

Restart Codex, open `/plugins`, choose `AgentMail Collab`, and install
`agentmail`.

Now move to the project where you want Claude Code and Codex to collaborate:

```bash
cd /path/to/your-project
```

Start Claude Code with channel support while Claude channels are in research
preview:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

Then join a room inside Claude Code. Room and agent names are yours to choose;
the first agent to join creates the room:

```text
/agentmail:start <room> <agent>
```

For example:

```text
/agentmail:start ecommerce claude
```

If you only need explicit mailbox access from a normal Codex TUI, ask Codex:

```text
Use @agentmail. Join room ecommerce as codex, list peers, and check my inbox.
```

For active Claude-to-Codex wakeups, launch Codex through AgentMail from the
project you want both agents to work on:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

Resume the most recent Codex session through the same wakeup path:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

If you already opened a normal Codex TUI, bootstrap a new AgentMail-aware
Remote TUI:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

The original normal Codex TUI cannot be injected directly through the current
plugin/MCP layer. Continue active-wakeup collaboration in the new Remote TUI.

Do not globally export `AGENTMAIL_DB=$HOME/.agentmail/agentmail.db` in your
shell startup files. Keep the database per project, or set `AGENTMAIL_DB` /
`AGENTMAIL_WORKSPACE` only in the shell for one project. See the
[install guide](docs/INSTALL.md) for the full global-install workflow.

## Common Workflow

1. Open Claude Code and Codex in the same project.
2. Start Claude Code with AgentMail channel support and run
   `/agentmail:start <room> claude`.
3. Start Codex with `agentmail launch-codex --room <room> --workspace "$PWD"`
   when you want inbound Claude messages to wake Codex.
4. Ask one agent to coordinate with the other. Agents send natural-language
   messages, claim file scope before editing shared areas, and register long
   outputs as artifacts instead of pasting everything into chat.
5. Use `agentmail doctor --room <room> --workspace "$PWD"` when setup looks
   wrong.

## Stable And Experimental Surfaces

Stable in this release:

- SQLite mailbox, rooms, threads, message status, artifacts, and scope claims.
- CLI commands and stdio MCP tools.
- Claude Code plugin package and Claude channel delivery.
- Codex plugin package for explicit mailbox use.

Experimental in this release:

- Codex App Server bridge (`agentmail launch-codex`,
  `agentmail bootstrap-codex`, and `agentmail codex-bridge ...`). It depends on
  Codex App Server and Remote TUI APIs and may change in a future release.

## Documentation

- [Install guide](docs/INSTALL.md)
- [Documentation index](docs/README.md)
- [Concepts](docs/CONCEPTS.md)
- [Architecture and module map](docs/ARCHITECTURE.md)
- [Claude channels](docs/CHANNELS.md)
- [Codex bridge](docs/CODEX_BRIDGE.md)
- [CLI reference](docs/CLI_REFERENCE.md)
- [MCP reference](docs/MCP_REFERENCE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Testing](docs/TESTING.md)
- [Release checklist](docs/RELEASE.md)
- [FAQ](docs/FAQ.md)
- [中文文档入口](docs/zh-CN/README.md)

## Repository Layout

```text
agentmail/
  .claude-plugin/marketplace.json  Claude Code marketplace entrypoint
  .agents/plugins/marketplace.json Codex marketplace entrypoint
  pyproject.toml                   Python package metadata
  *.py                             Core package modules
  docs/                            User, operator, and maintainer docs
  skills/                          Source skill guidance for Claude and Codex
  plugins/                         Self-contained Claude Code and Codex plugin payloads
  scripts/                         Local install and validation helpers
  tests/                           Unit and integration tests
```

AgentMail intentionally ships no plugin `agents/` definitions. Agent behavior
is negotiated in message bodies instead of being packaged as a fixed workflow.

## Development

Run the validation script before publishing or opening a PR:

```bash
./scripts/validate.sh
```

If you change core Python modules, run:

```bash
python plugins/sync_vendor.py
```

The plugin payloads are self-contained and vendor the Python runtime under
their plugin roots so installed plugins do not reference files outside the
client cache.

## Security

AgentMail is local, but peer messages are still untrusted input. Review shell
commands and destructive changes before running them. Do not commit
`.agentmail/`, because the database can contain project context, paths, and
agent messages.

Claude channel support currently requires:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

Use that flag only for local plugins you trust. See [SECURITY.md](SECURITY.md)
for the full local security model.
