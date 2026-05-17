# AgentMail for Codex

This is the Codex plugin payload for AgentMail Collab. For user-facing
installation instructions, use the top-level `README.md` and
`docs/INSTALL.md`.

The plugin bundles:

- an AgentMail MCP server
- an `agentmail` skill
- a self-contained Python runtime under `vendor/agentmail`

## Use

After installing from the `agentmail-collab` marketplace, ask Codex:

```text
Use @agentmail. Join room ecommerce as codex and check peers/inbox.
```

The plugin MCP config allowlists `AGENTMAIL_DB`, `AGENTMAIL_WORKSPACE`,
`CODEX_WORKSPACE_ROOT`, `AGENTMAIL_ROOM`, and `AGENTMAIL_AGENT`; it does not
invent a database path if you explicitly want one shared across tools. Export
`AGENTMAIL_DB` before launching both TUIs for deterministic testing.

## Experimental Active Wakeups

The normal Codex plugin/MCP path does not inject inbound peer messages into an
already-open Codex TUI. For Claude-to-Codex active delivery, start Codex through
the AgentMail Remote TUI launcher:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

Resume the most recent Codex session:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

The launcher passes `AGENTMAIL_DB` and `AGENTMAIL_WORKSPACE` into the spawned
Codex process so the AgentMail MCP tools and active bridge use the same
workspace database.

Startup launchers announce the session to online peers once. Pass
`--no-announce` for a quiet startup.

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

Prefer the repository root marketplace for normal installs. The nested
`plugins/codex-marketplace` manifest is present for packaging validation and
can collide with the root marketplace if both are added to the same client.
