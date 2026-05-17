# Codex Bridge

Codex bridge 通过 Codex App Server 和 Remote TUI 模式,把 AgentMail inbox message 投递进 Codex。

本 release 中 bridge 仍是实验能力。它依赖 Codex App Server 和 Remote TUI API,这些 API 未来可能变化。

## 为什么需要它

Claude Code 有 channels,可以把 AgentMail 消息注入正在运行的 Claude Code 会话。普通 Codex plugin / MCP session 目前没有同等注入路径。因此 AgentMail 使用 Codex App Server 作为 Claude → Codex 主动唤醒 adapter。

## 推荐 launcher

在项目目录运行:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

恢复最近一次 Codex 会话:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

恢复指定会话:

```bash
agentmail launch-codex \
  --room ecommerce \
  --workspace "$PWD" \
  --resume 019e3459-262e-7f53-b30d-a6c199f67606
```

`launch-codex` 会启动:

- `codex app-server`
- AgentMail bridge loop
- `codex --remote <listen-url>`

它会把 `AGENTMAIL_DB` 和 `AGENTMAIL_WORKSPACE` 传入 Codex 进程,保证 MCP tools 和 bridge 使用同一个数据库。

## 从普通 Codex TUI bootstrap

如果你已经打开了普通 Codex TUI,让它运行:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

要在新的 Remote TUI 中恢复最近会话:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD" --resume last
```

原来的普通 TUI 仍然是普通 TUI。主动唤醒协作应在新的 Remote TUI 里继续。

## 投递模式

`turn-start` 是默认模式:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --mode turn-start
```

它调用 Codex App Server `turn/start`,会启动一次 Codex model turn。每条 peer message 都可能消耗 Codex API budget。

`inject` 只追加上下文,不启动 model turn:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --mode inject
```

它调用 `thread/inject_items`。如果你只希望消息出现在 thread 里,等用户后续提交 turn 再运行 Codex,就用这个模式。

## 手动拆开运行

你也可以自己启动各个组件:

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

调试时可以让 bridge loop 在前台跑:

```bash
agentmail codex-bridge watch \
  --agent codex \
  --room ecommerce \
  --workspace "$PWD" \
  --listen ws://127.0.0.1:4500 \
  --once
```

## Thread 选择

如果只加载了一个 Codex thread,AgentMail 可以自动定位。如果加载了多个 thread,请传 `--thread-id`:

```bash
agentmail launch-codex \
  --room ecommerce \
  --workspace "$PWD" \
  --thread-id <codex-thread-id>
```

AgentMail 不能仅从 App Server 协议推断前台 TUI thread。

## 状态和日志

```bash
agentmail codex-bridge status --agent codex --room ecommerce --workspace "$PWD"
```

bridge 状态存放在:

```text
<workspace>/.agentmail/codex-bridge/
<workspace>/.agentmail/logs/
```

停止受管理的 bridge 进程:

```bash
agentmail codex-bridge stop --agent codex --room ecommerce --workspace "$PWD"
```

## 投递语义

- bridge 轮询 Codex agent inbox。
- bridge 跳过自己发出的消息。
- bridge 用每条消息独立的随机 fence 包住 AgentMail body。
- 只有 Codex App Server 调用成功后才标记 `delivered`。
- 如果投递失败,运行中的 bridge 会在后续 poll 重试。
- Codex 实际处理后仍然应该 mark `seen`、`claimed` 或 `resolved`。

## 安全说明

优先使用 localhost App Server endpoint,例如 `ws://127.0.0.1:4500`。不要把 bridge 指向你不控制的 endpoint。一次成功投递会让 Codex 把 peer message 作为模型可见输入处理。

bridge 支持 websocket continuation frame,并会校验受管理 `codex app-server` 进程的本地 readiness。
