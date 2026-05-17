# 主动投递

AgentMail 使用一个共享 mailbox,再通过 runtime-specific wakeup adapter 把新消息送进正在运行的 agent 会话。

## Claude Channel 投递

AgentMail 的 Claude Code 集成使用 Claude channels,把 inbox message 推到当前运行的 Claude Code TUI 会话。

## 工作方式

1. AgentMail MCP server 声明实验性的 `claude/channel` capability。
2. `/agentmail:start <room> <agent>` 写入 `.agentmail/channel.json`,记录 active room 和 Claude agent 名。
3. MCP server 轮询该 inbox,对新消息发出 `notifications/claude/channel`。
4. Claude Code 把每个 notification 注入成当前会话里的 `<channel ...>` event。
5. Claude 可以调用 `agentmail_reply` 或 `agentmail_send` 响应。

channel event body 就是原始 AgentMail message body。路由元数据放在属性里,例如
`room`、`message_id`、`from_agent`、`thread_id`、`trace_id`、`subject`。

## 要求

Claude channels 当前是 research preview。启动 Claude Code 时使用:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

Team / Enterprise organization 还可能需要在策略里允许 channels。

## 投递语义

- Channel notification 通过 MCP stdio 写给 Claude Code。
- AgentMail 发出 notification 后把消息标记为 `delivered`。
- Claude 开始处理时应该把消息标记为 `seen` 或 `claimed`。
- 如果 Claude 用 `agentmail_reply` 回复,原消息可以同时 resolve。

notification 不是 Claude Code 自身的 durable acknowledgement。端到端确认仍然应该看 AgentMail message status 和 reply。

## Codex App Server Bridge

Codex 目前没有等价于 Claude channel 的 plugin/MCP notification 能力,不能直接把 inbound message 注入一个已经打开的普通 TUI。实验性的 AgentMail Codex bridge 使用 Codex App Server 实现主动唤醒。

启动一个受管理的 Remote TUI:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

恢复最近一次 Codex 会话:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

launcher 会把 `AGENTMAIL_DB` 和 `AGENTMAIL_WORKSPACE` 注入新启动的 Codex 进程,保证 Codex MCP tool calls 和 Remote TUI bridge 使用同一个数据库。

startup command 加入 room 时,AgentMail 会向在线 peer 发送去重的 discovery message。它只是 presence signal;正文仍然是普通 AgentMail 内容,接收方自行决定如何处理。

如果你已经在普通 Codex TUI 里,用 bootstrap wrapper 打开一个新的 AgentMail-aware Remote TUI:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

也可以连接你自己启动的 server:

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

bridge 会轮询 Codex agent inbox。对来自其他 agent 的每条新消息,它调用 Codex App Server:

- 默认 `turn-start` 模式调用 `turn/start`。
- `inject` 模式调用 `thread/inject_items`。

`turn-start` 会为每条投递消息启动一次 Codex model turn,因此会消耗 Codex API budget。`inject` 不会自行运行模型,只把消息加入目标 thread,等待后续用户驱动的 turn。

App Server 调用成功后,AgentMail 把消息标记为 `delivered`。Codex 真正处理后仍然应该把消息标记为 `seen`、`claimed` 或 `resolved`。

如果加载了多个 Codex thread,请传 `--thread-id`。AgentMail 不能仅从 App Server 协议推断前台 TUI thread。
