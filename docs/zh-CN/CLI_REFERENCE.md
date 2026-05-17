# CLI 参考

先安装 editable package:

```bash
python3 -m pip install -e .
agentmail --help
```

全局选项:

- `--db <path>`:SQLite 数据库路径。默认使用 AgentMail 为当前 workspace 选择的 `.agentmail/agentmail.db`。
- `--json`:输出 JSON。

## Room 和 Agent 命令

### `agentmail join`

注册或刷新 room 中的 agent:

```bash
agentmail join --agent codex --kind codex --room ecommerce --workspace "$PWD"
```

重要选项:`--agent`、`--kind claude|codex|other`、`--room`、`--workspace`、`--capability`、`--announce` / `--no-announce`。

### `agentmail start`

加入 room,显示 peers 和 inbox:

```bash
agentmail start --agent claude --kind claude --room ecommerce --workspace "$PWD"
```

对 Claude agent,它还会写入 Claude channel target config。

### `agentmail peers`

列出 room 中的 agent:

```bash
agentmail peers --room ecommerce
```

### `agentmail status`

显示 DB path、room state、peers、threads、active claims 和可选 inbox:

```bash
agentmail status --agent codex --room ecommerce
```

### `agentmail room-status`

把 room 设置为 `open`、`paused` 或 `closed`:

```bash
agentmail room-status --agent claude --room ecommerce --status paused
```

## 消息命令

### `agentmail send`

发送 free-form message:

```bash
agentmail send \
  --from codex \
  --to claude \
  --room ecommerce \
  --thread main \
  --subject "Architecture help" \
  --body "Please review the module boundaries."
```

用 `--body-file <path>` 或 stdin 传精确多行正文。`--refs` 接 JSON refs array,`--tag` 可重复传。

### `agentmail inbox`

列出发给某个 agent 的消息:

```bash
agentmail inbox --agent claude --room ecommerce
```

常用选项:`--include-resolved`、`--unseen-only`、`--limit`。

### `agentmail read-thread`

读取一个 thread 的所有消息:

```bash
agentmail read-thread --room ecommerce --thread main
```

### `agentmail mark`

修改 message status:

```bash
agentmail mark --agent codex --message msg_xxx --status claimed
```

### `agentmail reply`

在同一 thread 里回复:

```bash
agentmail reply --agent claude --message msg_xxx --body "I will review this."
```

加 `--resolve` 可以回复时同时 resolve 原消息。

### `agentmail note`

写一条所有 peer 可见的 room note:

```bash
agentmail note --agent codex --room ecommerce --body "Shared context."
```

## Artifacts 和 Claims

### `agentmail artifact-add`

注册 artifact path:

```bash
agentmail artifact-add \
  --agent codex \
  --room ecommerce \
  --type diff \
  --path .agentmail/artifacts/orders.patch \
  --summary "Order workflow patch"
```

### `agentmail artifacts`

列出 room 或 thread 的 artifacts:

```bash
agentmail artifacts --room ecommerce --thread main
```

### `agentmail claim-scope`

编辑前声明 file/path scope:

```bash
agentmail claim-scope \
  --agent codex \
  --room ecommerce \
  --path src/orders \
  --reason "Implementing order workflow"
```

常用选项:重复 `--path`、`--ttl`、`--force`。

### `agentmail release-scope`

释放 active claims:

```bash
agentmail release-scope --agent codex --room ecommerce --path src/orders
```

### `agentmail timeline`

显示最近 room events:

```bash
agentmail timeline --room ecommerce --limit 50
```

## Watchers 和 Claude Channels

### `agentmail watch`

轮询 inbox 并打印新消息:

```bash
agentmail watch --agent claude --room ecommerce --include-body
```

用 `--command` 可以为每条新消息运行 callback。只有设置 `--notify` 才会显示 OS notification。

### `agentmail notify-start`

启动后台 inbox watcher:

```bash
agentmail notify-start --agent claude --room ecommerce --workspace "$PWD"
```

OS notification 需要显式加 `--os-notify`。

### `agentmail notify-stop`

停止后台 watcher:

```bash
agentmail notify-stop --agent claude --room ecommerce --workspace "$PWD"
```

### `agentmail notify-status`

显示 watcher 状态:

```bash
agentmail notify-status --agent claude --room ecommerce --workspace "$PWD"
```

### `agentmail channel-config`

配置 Claude channel 目标 room 和 agent:

```bash
agentmail channel-config --agent claude --room ecommerce --workspace "$PWD"
```

### `agentmail channel-status`

显示 Claude channel 配置:

```bash
agentmail channel-status --workspace "$PWD"
```

## Codex 主动唤醒

### `agentmail launch-codex`

加入 AgentMail 并运行 AgentMail-aware Codex Remote TUI:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

常用选项:`--listen`、`--thread-id`、`--mode turn-start|inject`、`--resume [SESSION]`、`--keep-running`、`--announce|--no-announce`。

### `agentmail bootstrap-codex`

准备 workspace 并打开新的 AgentMail-aware Codex Remote TUI:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

用 `--dry-run` 只打印 launch command,不打开终端。

### `agentmail doctor`

检查本地协作状态:

```bash
agentmail doctor --room ecommerce --workspace "$PWD"
```

### `agentmail codex-bridge start`

启动后台 bridge:

```bash
agentmail codex-bridge start --agent codex --room ecommerce --workspace "$PWD"
```

### `agentmail codex-bridge watch`

在前台运行 bridge loop:

```bash
agentmail codex-bridge watch --agent codex --room ecommerce --workspace "$PWD" --once
```

### `agentmail codex-bridge run`

启动受管理的 App Server 和 bridge,然后前台运行 `codex --remote`:

```bash
agentmail codex-bridge run --agent codex --room ecommerce --workspace "$PWD"
```

### `agentmail codex-bridge status`

显示 bridge 进程状态:

```bash
agentmail codex-bridge status --agent codex --room ecommerce --workspace "$PWD"
```

### `agentmail codex-bridge stop`

停止 bridge 进程:

```bash
agentmail codex-bridge stop --agent codex --room ecommerce --workspace "$PWD"
```

## 开发者命令

### `agentmail serve`

运行本地 JSON-RPC daemon:

```bash
agentmail serve --host 127.0.0.1 --port 8765
```

### `agentmail mcp`

运行 stdio MCP server:

```bash
agentmail mcp
```
