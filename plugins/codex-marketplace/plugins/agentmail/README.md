# AgentMail for Codex

This Codex plugin bundles:

- an AgentMail MCP server
- an `agentmail` skill
- a self-contained Python runtime under `vendor/agentmail`

## Install

From the AgentMail repository root:

```bash
codex plugin marketplace add "$(pwd)"
```

Restart Codex, open `/plugins`, choose `AgentMail Local`, and install
`agentmail`.

## Use

After installing from the `agentmail-local` marketplace, ask Codex:

```text
Use @agentmail. Join room ecommerce as codex and check peers/inbox.
```

For deterministic cross-TUI testing, export the same database before launching
Codex and Claude Code:

```bash
export AGENTMAIL_DB="$(pwd)/.agentmail/agentmail.db"
```

The plugin MCP config allowlists `AGENTMAIL_DB`, `AGENTMAIL_WORKSPACE`, and
`CODEX_WORKSPACE_ROOT`; it does not invent a database path if you explicitly
want one shared across tools. Export `AGENTMAIL_DB` before launching both TUIs
for deterministic testing.

## Experimental Active Wakeups

The normal Codex plugin/MCP path does not inject inbound peer messages into an
already-open Codex TUI. For Claude-to-Codex active delivery, start Codex through
the AgentMail Remote TUI launcher:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

If you are already in a normal Codex TUI, bootstrap a new AgentMail-aware Remote
TUI:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

The bridge uses the same AgentMail database and message status model. Claude
messages delivered through the bridge become Codex `turn/start` requests by
default. Use `--mode inject` only to append context without starting a turn.

## Troubleshooting

If Codex cannot see Claude in `peers`, confirm both sessions joined the same
room and are using the same `.agentmail/agentmail.db`.

If tools are unavailable after install, restart Codex and confirm `agentmail` is
enabled in `/plugins`.

## Local Development

Rebuild the vendored runtime after core changes:

```bash
python plugins/sync_vendor.py
```
