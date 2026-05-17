# Troubleshooting

## Claude And Codex Cannot See Each Other

Check they are using the same database:

```bash
python -m agentmail status --agent codex --room ecommerce
python -m agentmail status --agent claude --room ecommerce
```

For deterministic testing, export a shared database before launching both TUIs:

```bash
export AGENTMAIL_DB="$(pwd)/.agentmail/agentmail.db"
```

If using MCP tools, join with the current workspace path first. The MCP server
binds follow-up calls to that workspace database after `agentmail_join`.

## Claude Does Not Wake Up

Confirm Claude Code was launched with the channel development bypass:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-local
```

Then run:

```text
/agentmail:start ecommerce claude
```

Check the channel target:

```bash
python -m agentmail channel-status --workspace "$PWD"
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
python -m agentmail notify-start --agent claude --room ecommerce --workspace "$PWD" --os-notify
```

## Claude Does Not Wake Codex

Normal Codex TUI sessions cannot currently be injected through the AgentMail
plugin/MCP server. Use the experimental Codex App Server bridge:

```bash
python -m agentmail codex-bridge run \
  --agent codex \
  --room ecommerce \
  --workspace "$PWD" \
  --listen ws://127.0.0.1:4500
```

Check bridge status:

```bash
python -m agentmail codex-bridge status --agent codex --room ecommerce --workspace "$PWD"
```

If more than one Codex thread is loaded, restart with `--thread-id <id>`.
If `app_server_running` is false, inspect `.agentmail/logs/*codex-app-server.log`.

## Plugin Changes Do Not Load

Marketplace-installed plugins are copied into client caches. After changing a
plugin package:

```bash
python plugins/sync_vendor.py
claude plugin marketplace update agentmail-local
```

For local development, reinstalling from the repository root is often clearer:

```bash
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-local --scope local
codex plugin marketplace add "$(pwd)"
```

Restart the TUI after plugin changes that affect MCP servers, commands, or
skills.
