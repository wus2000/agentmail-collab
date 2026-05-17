# AgentMail Plugin Packages

This directory contains the installable plugin payloads for both Codex and
Claude Code. The formal marketplace entrypoints live at the `agentmail/`
repository root:

- `agentmail/.claude-plugin/marketplace.json`
- `agentmail/.agents/plugins/marketplace.json`

The plugin packages are self-contained: each plugin bundles a copy of the
AgentMail Python package under `vendor/`, so installed plugins do not need to
reference files outside their plugin cache directory.

## Layout

```text
plugins/
  codex-marketplace/
    .agents/plugins/marketplace.json
    plugins/agentmail/
      .codex-plugin/plugin.json
      .mcp.json
      skills/agentmail/SKILL.md
      bin/agentmail
      bin/agentmail-mcp
      vendor/agentmail/
  claude-marketplace/
    .claude-plugin/marketplace.json
    plugins/agentmail/
      .claude-plugin/plugin.json
      .mcp.json
      skills/agentmail/SKILL.md
      commands/start.md
      commands/status.md
      bin/agentmail
      bin/agentmail-mcp
      vendor/agentmail/
```

## Rebuild Bundled Core

Run this after changing the core package:

```bash
python agentmail/plugins/sync_vendor.py
```

## Install In Claude Code

From the `agentmail/` directory:

```bash
claude plugin validate .
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-local --scope local
```

Restart or run `/reload-plugins`, then start a room:

```text
/agentmail:start ecommerce claude
```

To let AgentMail wake the already-running Claude Code session, start Claude
Code with channels enabled for the local plugin. During Claude Code's research
preview, local plugins need the development-channel bypass:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-local
```

After `/agentmail:start ecommerce claude`, the plugin records that room as the
active AgentMail channel target. Future messages addressed to `claude` in that
room are pushed into the current Claude Code session as channel events.

## Install In Codex

From the `agentmail/` directory:

```bash
codex plugin marketplace add "$(pwd)"
```

Restart Codex, open the plugin directory, choose `AgentMail Local`, and install
`agentmail`. Then ask Codex to use `$agentmail` and join the same room:

```text
Use @agentmail. Join room ecommerce as codex, list peers, and check my inbox.
```

In the Codex CLI, the plugin directory is opened with `/plugins`.

For Claude-to-Codex active wakeups, start Codex through the experimental App
Server bridge instead of a normal TUI:

```bash
python -m agentmail launch-codex --room ecommerce --workspace "$PWD"
```

From an already-open normal Codex TUI:

```bash
python -m agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

This uses the same mailbox and message status model. The bridge delivers
Claude-origin inbox messages into Codex through Codex App Server `turn/start`.

## Shared Database

By default AgentMail uses `<workspace>/.agentmail/agentmail.db`. The wrapper
uses the workspace exposed by the client, and the MCP server also binds itself
to the `workspace` passed on the first `agentmail_join` call. If neither is
available, it falls back to:

```text
~/.agentmail/agentmail.db
```

For deterministic testing across both TUIs, set this before launching both
Codex and Claude Code:

```bash
export AGENTMAIL_DB="$(pwd)/.agentmail/agentmail.db"
```

Message bodies remain opaque and exact. Only envelope fields such as sender,
recipients, room, thread, refs, tags, and status are structured.

## Background Notifications

Claude channels are the primary wakeup path for Claude Code. `/agentmail:start`
only joins the room and configures the channel target; it does not start a
watcher or show macOS notifications.

If you still need a manual fallback, `/agentmail:notify-start` starts a
background watcher for logs or command callbacks. It does not show OS
notifications by default. You can manage it manually:

```text
/agentmail:notify-start ecommerce claude
/agentmail:status ecommerce claude
/agentmail:notify-stop ecommerce claude
```

The underlying CLI also supports command callbacks:

```bash
python -m agentmail notify-start \
  --agent claude \
  --room ecommerce \
  --workspace "$PWD" \
  --command 'jq -r .subject >> .agentmail/notifications.log'
```

The callback receives the full message JSON on stdin and message metadata in
`AGENTMAIL_MESSAGE_ID`, `AGENTMAIL_FROM`, `AGENTMAIL_SUBJECT`,
`AGENTMAIL_TRACE_ID`, and `AGENTMAIL_THREAD_ID`.
