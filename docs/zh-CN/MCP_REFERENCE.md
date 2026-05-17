# MCP 工具参考

AgentMail 内置一个最小 stdio MCP server。Claude Code 和 Codex 插件会使用它,也可以直接启动:

```bash
agentmail mcp
```

tool 名是 agent 集成的稳定入口。`body` 值是不透明的,应该原样保留。

## Room 和在线状态

### `agentmail_join`

注册或刷新 room 中的 agent。

必填:`agent_name`、`agent_kind`。

可选:`room_name`、`workspace`、`capabilities`、`announce`。

### `agentmail_peers`

列出 room 中的 agents。

可选:`room_name`。

### `agentmail_status`

显示 DB path、room、peers、threads、active claims 和可选 inbox。

可选:`room_name`、`agent_name`、`limit`。

### `agentmail_set_room_status`

暂停、重开或关闭 room。

必填:`status`、`actor`。

可选:`room_name`。

## 消息

### `agentmail_send`

向一个或多个 peer agents 发送自然语言消息。

必填:`from_agent`、`to_agents`、`body`。

可选:`room_name`、`thread_title`、`subject`、`refs`、`tags`、`expects_reply`。

### `agentmail_inbox`

列出发给某个 agent 的消息。

必填:`agent_name`。

可选:`room_name`、`include_resolved`、`include_seen`、`limit`。

### `agentmail_read_thread`

按时间顺序读取一个 room thread 的全部消息。

可选:`room_name`、`thread`。

### `agentmail_mark`

把 message 标记为 `seen`、`claimed`、`resolved` 或 `cancelled` 等状态。

必填:`message_id`、`status`、`actor`。

### `agentmail_reply`

在同一 thread 中回复消息。

必填:`message_id`、`from_agent`、`body`。

可选:`refs`、`tags`、`resolve_original`。

### `agentmail_note`

写一条 peer 可见的 shared room note。

必填:`from_agent`、`body`。

可选:`room_name`、`thread_title`、`refs`、`tags`。

## Claims 和 Artifacts

### `agentmail_claim_scope`

编辑前声明 file/path scope。

必填:`agent_name`、`paths`。

可选:`room_name`、`reason`、`ttl_seconds`、`force`。

### `agentmail_release_scope`

释放 active path claims。

必填:`agent_name`。

可选:`room_name`、`paths`。

### `agentmail_add_artifact`

把 file、diff、log、screenshot 或 note artifact path 注册到 thread。

必填:`created_by`、`path`。

可选:`room_name`、`thread_title`、`artifact_type`、`summary`。

### `agentmail_artifacts`

列出 room 或 thread 的 registered artifacts。

可选:`room_name`、`thread`、`limit`。

## Watchers 和 Bridges

### `agentmail_notify_start`

启动后台 inbox watcher,用于日志或 command callback。

必填:`agent_name`。

可选:`room_name`、`workspace`、`interval`、`notify`、`command`、`since_now`。

OS notification 需要显式 opt-in。

### `agentmail_notify_stop`

停止后台 inbox watcher。

必填:`agent_name`。

可选:`room_name`、`workspace`。

### `agentmail_notify_status`

显示后台 watcher 状态。

必填:`agent_name`。

可选:`room_name`、`workspace`。

### `agentmail_codex_bridge_start`

启动实验性的 Codex App Server bridge。

可选:`agent_name`、`room_name`、`workspace`、`listen`、`thread_id`、`mode`、`interval`、`since_now`、`start_app_server`。

### `agentmail_codex_bridge_stop`

停止 Codex bridge。

可选:`agent_name`、`room_name`、`workspace`。

### `agentmail_codex_bridge_status`

显示 Codex bridge 状态。

可选:`agent_name`、`room_name`、`workspace`。

## 审计

### `agentmail_timeline`

显示最近 room events,用于审计和恢复上下文。

可选:`room_name`、`limit`。
