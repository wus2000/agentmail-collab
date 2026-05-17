# 架构

AgentMail Collab 的核心是一个 mailbox,外围是不同 runtime 的投递 adapter。

```text
            Claude Code TUI                         Codex Remote TUI
                  |                                      |
      Claude channel notification              Codex App Server websocket
                  |                                      |
            mcp_server.py                         codex_bridge.py
                  |                                      |
                  +--------------+---------------+
                                 |
                           service.py
                                 |
                            store.py
                                 |
                    <workspace>/.agentmail/agentmail.db
```

## 设计原则

- AgentMail 是 mailbox,不是 orchestrator。
- AgentMail 把 Claude Code 和 Codex 当作平等 peer;谁都不是主控,谁也不是对方的工具。
- 消息正文是 opaque 且 exact 的。AgentMail 不解析、不分类、不改写、不模板化、不校验、不裁剪 body。
- 结构化协议保持很小:envelope、status、refs、tags、artifacts、scope claims。凡是能放在 body 里的内容,都放在 body 里。
- 工作流存在于 agent 对话中,不硬编码在协调逻辑里。
- 两个 adapter,一个 mailbox:Claude Code 使用 MCP 发出的 channel event;Codex 使用连接 App Server 的外部 bridge。两者都读取同一个 `service.inbox(...)`,也写入同一套 `status` 状态。

## 部署形态

AgentMail Collab 把**工具**和**数据**分开:

- 工具:CLI、插件载荷、vendored Python runtime。可以安装一次,跨项目复用。
- 数据:SQLite mailbox、channel target、bridge 状态、日志。始终按项目隔离。

```text
GLOBAL (安装一次)                         PER WORKSPACE (每个项目一份)
──────────────────                        ───────────────────────────
~/.local/bin/agentmail                    <project>/.agentmail/
  (或 pip 安装到的位置)                      ├── agentmail.db
                                            ├── channel.json
~/.claude/plugins/.../agentmail/            ├── codex-bridge/
  (user-scope plugin payload)               │     <room>-<agent>.pid
  ├── .claude-plugin/plugin.json            │     <room>-<agent>.json
  ├── .mcp.json                             ├── logs/
  ├── bin/                                  │     <room>-<agent>.codex-bridge.log
  ├── commands/                             │     <room>-<agent>.codex-app-server.log
  ├── skills/                               └── watch/<room>-<agent>.pid
  └── vendor/agentmail/

~/.codex/plugins/.../agentmail/
  (personal Codex plugin payload,结构相同)
```

因此:

1. **不要全局 export `AGENTMAIL_DB`**。否则所有项目会共用一个 room 命名空间。
2. **MCP server 会拒绝 plugin-cache DB fallback**。从 v0.1.0 开始,如果 MCP server 无法推断 workspace,它会报错,不会在 plugin cache 里静默创建 DB。首次 tool call 应传 `workspace`,或设置 `AGENTMAIL_WORKSPACE` / `CODEX_WORKSPACE_ROOT` / `CLAUDE_PROJECT_DIR`。

推荐的 Codex 主动唤醒入口是:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

这个 launcher 会把 `AGENTMAIL_DB` 和 `AGENTMAIL_WORKSPACE` 传给新开的 Codex Remote TUI,保证 MCP tools 和 bridge 使用同一个项目数据库。

## Core Mailbox

`service.py` 提供不绑定工作流的应用操作:join、send、inbox、read thread、mark、reply、claim scope、release scope、add artifacts、inspect timeline、set room status。

`store.py` 负责 SQLite 持久化、schema 创建、row 转换、UTC timestamp、ID 和 append-only event timeline。

## Transport Adapters

Claude Code 使用 `mcp_server.py` 和 Claude channels。Claude 加入 room 后,AgentMail 会在 `.agentmail/` 下写入 channel 配置。MCP server 轮询目标 inbox,并向当前 Claude Code 会话发出 `notifications/claude/channel` event。

Codex 使用 `codex_bridge.py` 做主动唤醒。bridge 连接 Codex App Server,并通过 `turn/start` 或 `thread/inject_items` 投递 inbound message。普通 Codex plugin/MCP session 不能被直接注入,所以主动唤醒需要 Remote TUI 模式。

## Plugins And Skills

插件包通过 MCP 和 wrapper script 把 Claude Code / Codex 接到本地 mailbox。skill 教 agent 什么时候、怎么使用 mailbox。按 OpenAI 的术语,plugin 提供 tool/data access,skill 提供可重复的过程指导。

AgentMail 故意不附带插件级 `agents/` 目录。agent 行为通过消息正文协商,而不是作为固定 subagent persona 打包。

## 组件和模块地图

代码库刻意保持小。贡献者通常先看这张表即可:

```text
Module             Role
models.py          Domain dataclasses
store.py           SQLite persistence, schema creation, IDs, timestamps, events
service.py         Workflow-free application API and domain validation
cli.py             argparse CLI surface and launch/bootstrap commands
mcp_server.py      stdio MCP tools and Claude channel delivery
notify.py          Watcher process management and channel config helpers
codex_bridge.py    Codex App Server bridge and Remote TUI delivery
daemon.py          Optional local JSON-RPC daemon
```

### Core Domain

- `models.py`:room、agent、thread、message、artifact、scope claim 的 dataclass。纯数据,无 I/O。
- `store.py`:SQLite schema、open 时迁移、row 转换、ID helper、timestamp helper、event 记录和默认 DB 路径解析。
- `service.py`:应用级操作和领域校验。join、send、mark、claim、artifact registration、channel config、discovery notice 等公共流程都在这里,而不是散落在 surface 层。

### Interfaces And Packaging

- `cli.py`:`agentmail ...` 命令集合,包括 mailbox 操作、watcher、channel config、Codex launch/bootstrap、bridge 管理、doctor、daemon 和 MCP server 启动。见 [CLI_REFERENCE.md](CLI_REFERENCE.md)。
- `mcp_server.py`:stdio MCP server,提供 AgentMail tools,并在 `AGENTMAIL_CHANNEL=1` 时启用 Claude channel delivery。见 [MCP_REFERENCE.md](MCP_REFERENCE.md)。
- `notify.py`:watcher process 管理、command callback、OS notification opt-in、channel config helper。
- `codex_bridge.py`:Codex App Server client、bridge lifecycle、WebSocket framing、delivery modes、status file 和 Remote TUI launch 支持。见 [CODEX_BRIDGE.md](CODEX_BRIDGE.md)。
- `daemon.py`:可选的本地 JSON-RPC daemon。

插件载荷在 `plugins/claude-marketplace/plugins/agentmail/` 和
`plugins/codex-marketplace/plugins/agentmail/` 下。`plugins/sync_vendor.py` 会把
源码包同步到它们的 `vendor/agentmail/`,让安装后的插件自包含。

## 数据流

```text
   sender                    mailbox            adapter            receiver
   ──────                    ───────            ───────            ────────
   send ───── store.message ─→  queued
                                  │
                                  └─── inbox poll ──→ deliver ─→  delivered
                                                                    │
                                                          channel  │ bridge
                                                          event  ──┴── ws frame
                                                                    │
                                                                    ▼
                                                                   seen
                                                                    │
                                                                  claimed
                                                                    │
                                                                  replied
                                                                    │
                                                                  resolved
```

1. agent 加入 room,并可选择向 peer 发送 discovery notice。
2. peer 通过 CLI 或 MCP 发送消息。
3. 消息以 `queued` 状态存入双方 adapter 共用的 SQLite mailbox。
4. 投递 adapter(Claude channel 或 Codex bridge)通过同一个 `service.inbox(...)` 过滤器看到 inbox item。
5. adapter 投递成功后把消息标记为 `delivered`。
6. 接收方 agent 把消息标记为 `seen` 或 `claimed`。
7. 接收方 reply、resolve,或注册 artifact。

status 是端到端协调信号。`delivered` 只表示 adapter 投递成功,不表示接收方已经完成工作;真正的处理进度由接收方的状态变更和 reply 证明。

## 扩展点

要支持另一个 agent runtime,新增 adapter 即可:

1. 以具名 agent 加入共享 room。
2. 读取或订阅该 agent 的 inbox。
3. 注入 runtime 时完整保留 message body。
4. 只有成功投递后才 mark message。
5. 把工作流决策留给接收方 agent。
