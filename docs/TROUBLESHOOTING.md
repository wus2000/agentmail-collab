# Troubleshooting

## Claude And Codex Cannot See Each Other

Check they are using the same database:

```bash
agentmail status --agent codex --room ecommerce
agentmail status --agent claude --room ecommerce
```

For deterministic testing, export a shared database before launching both TUIs:

```bash
export AGENTMAIL_DB="$(pwd)/.agentmail/agentmail.db"
```

If using MCP tools, join with the current workspace path first. The MCP server
binds follow-up calls to that workspace database after `agentmail_join`.

## My DB Landed In A Plugin Cache Directory

If `agentmail status` shows a database path containing `.claude/plugins/cache/`
or `.codex/plugins/cache/`, the MCP server fell back to the plugin cache cwd
because no workspace was passed. Starting in v0.1.0 the MCP server refuses to
create a DB inside a plugin cache and raises a clear error instead. To recover:

- Pass `workspace` explicitly when calling `agentmail_join` (and tell your
  agent skill to always do this on first join).
- Or export `AGENTMAIL_WORKSPACE="$PWD"` from your project directory before
  launching Claude Code or Codex.
- Or use the AgentMail-managed launcher for Codex active wakeups, which sets
  `AGENTMAIL_WORKSPACE` for you:

  ```bash
  agentmail launch-codex --room ecommerce --workspace "$PWD"
  ```

If you have already accumulated state inside a plugin cache from an older
build, locate it with:

```bash
find ~/.claude/plugins/cache ~/.codex/plugins/cache -name agentmail.db 2>/dev/null
```

Move or remove that file once you have confirmed nothing important lives in
it, then rejoin from your project with an explicit `workspace`.

## Claude Does Not Wake Up

Confirm Claude Code was launched with the channel development bypass:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

Then run:

```text
/agentmail:start ecommerce claude
```

Check the channel target:

```bash
agentmail channel-status --workspace "$PWD"
```

If messages are `delivered` in `timeline` but Claude does not respond, the MCP
server emitted the channel event and the issue is in Claude Code channel
handling or session policy. Check `/mcp` in Claude Code and the Claude debug
logs.

## No macOS Notification Appears

This is expected. AgentMail does not show OS notifications by default. Claude
channels are the primary wakeup path.

If you explicitly want a fallback watcher:

```bash
agentmail notify-start --agent claude --room ecommerce --workspace "$PWD" --os-notify
```

## Claude Does Not Wake Codex

Normal Codex TUI sessions cannot currently be injected through the AgentMail
plugin/MCP server. Use the experimental Codex App Server bridge:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

From an already-open normal Codex TUI, bootstrap a new AgentMail-aware Remote
TUI instead:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

Check bridge status:

```bash
agentmail codex-bridge status --agent codex --room ecommerce --workspace "$PWD"
```

If more than one Codex thread is loaded, restart with `--thread-id <id>`.
If `app_server_running` is false, inspect `.agentmail/logs/*codex-app-server.log`.

## Plugin Changes Do Not Load

Marketplace-installed plugins are copied into client caches. After changing a
plugin package:

```bash
python plugins/sync_vendor.py
claude plugin marketplace update agentmail-collab
```

For local development, reinstalling from the repository root is often clearer:

```bash
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-collab --scope local
codex plugin marketplace add "$(pwd)"
```

Restart the TUI after plugin changes that affect MCP servers, commands, or
skills.
