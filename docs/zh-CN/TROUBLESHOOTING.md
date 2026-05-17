# 故障排查

## Claude 和 Codex 看不到彼此

先确认它们使用同一个数据库:

```bash
agentmail status --agent codex --room ecommerce
agentmail status --agent claude --room ecommerce
```

做确定性测试时,在启动两个 TUI 前导出同一个 DB:

```bash
export AGENTMAIL_DB="$(pwd)/.agentmail/agentmail.db"
```

如果使用 MCP tools,第一次 join 时传当前 workspace path。`agentmail_join` 后,MCP server 会把后续调用绑定到这个 workspace database。

## DB 落到了 plugin cache 目录

如果 `agentmail status` 显示 DB path 包含 `.claude/plugins/cache/` 或
`.codex/plugins/cache/`,说明旧版本 MCP server 曾经因为没有传 workspace 而 fallback 到 plugin cache cwd。

从 v0.1.0 开始,MCP server 会拒绝在 plugin cache 里创建 DB,并抛出明确错误。修复方式:

- 调用 `agentmail_join` 时显式传 `workspace`。
- 或在项目目录启动 Claude Code / Codex 前设置 `AGENTMAIL_WORKSPACE="$PWD"`。
- 或用 AgentMail-managed Codex launcher:

  ```bash
  agentmail launch-codex --room ecommerce --workspace "$PWD"
  ```

如果旧版本已经在 plugin cache 里留下 DB,可以先定位:

```bash
find ~/.claude/plugins/cache ~/.codex/plugins/cache -name agentmail.db 2>/dev/null
```

确认没有重要内容后再移动或删除,然后从项目目录重新 join。

## Claude 没有被唤醒

确认 Claude Code 启动时带了 channel development bypass:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

然后在 Claude Code 里运行:

```text
/agentmail:start ecommerce claude
```

检查 channel target:

```bash
agentmail channel-status --workspace "$PWD"
```

如果 `timeline` 里消息已经是 `delivered`,但 Claude 没有响应,说明 MCP server 已经发出了 channel event,问题可能在 Claude Code channel handling 或 session policy。检查 Claude Code 里的 `/mcp` 和 debug log。

## 没有 macOS 系统通知

这是预期行为。AgentMail 默认不显示 OS notification。Claude channels 是主要唤醒路径。

如果你确实想要 fallback watcher:

```bash
agentmail notify-start --agent claude --room ecommerce --workspace "$PWD" --os-notify
```

## Claude 不能唤醒 Codex

普通 Codex TUI 目前不能通过 AgentMail plugin/MCP server 被注入。请使用实验性的 Codex App Server bridge:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

如果你已经在普通 Codex TUI 里,打开一个新的 AgentMail-aware Remote TUI:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

检查 bridge 状态:

```bash
agentmail codex-bridge status --agent codex --room ecommerce --workspace "$PWD"
```

如果加载了多个 Codex thread,重新启动时传 `--thread-id <id>`。如果 `app_server_running` 是 false,检查 `.agentmail/logs/*codex-app-server.log`。

## 插件改动没有生效

marketplace 安装的插件会被复制到客户端 cache。修改插件包后:

```bash
python plugins/sync_vendor.py
claude plugin marketplace update agentmail-collab
```

本地开发时,从仓库根目录重装通常更清楚:

```bash
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-collab --scope local
codex plugin marketplace add "$(pwd)"
```

修改 MCP server、commands 或 skills 后,重启对应 TUI。
