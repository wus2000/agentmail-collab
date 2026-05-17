# 核心概念

AgentMail Collab 只提供基础的协作能力,不规定工作流。Claude Code 和 Codex
仍然通过自然语言自行协商计划、实现、审查和验收。

## Workspace

Workspace 是两个或更多 agent 协作的**本地项目目录**,通常就是某个 git 仓库
的根目录。AgentMail 把**所有**运行时状态都放在 `<workspace>/.agentmail/`
下面:

- `agentmail.db`:本项目的 SQLite mailbox(room、thread、message、artifact、
  scope claim、timeline 等)。
- `channel.json`:本 workspace 的 Claude Code channel 投递配置。
- `codex-bridge/`:bridge 的 pid 与配置(按 `<room>-<agent>` 分文件)。
- `logs/`:watcher 与 bridge 日志。

CLI 和 plugin 可以全局安装,但**数据始终按 workspace 隔离**。AgentMail 依
照 `--workspace`、`AGENTMAIL_WORKSPACE`、`CLAUDE_PROJECT_DIR`、
`CODEX_WORKSPACE_ROOT` 的顺序定位 workspace。v0.1.0 起,MCP server 拒绝
fallback 到 plugin cache 目录,会要求你显式指定 workspace。

## Room

Room 是一个项目或任务**在某个 workspace 内**的协作空间。通常 Claude Code
和 Codex 会在同一个 workspace 下加入同一个 room(例如 `ecommerce`)。Room
状态可以是 `open`、`paused` 或 `closed`。同一个 workspace 可以容纳多个
room;room 名只在该 workspace 的数据库内唯一,所以不要跨项目共享同一份
数据库。

## Agent

Agent 是 room 里的参与者,比如 `claude` 或 `codex`。AgentMail 不区分主从,
只记录名字、类型(kind)、workspace、心跳和声明的能力(capabilities)。

## Thread

Thread 是 room 内一组相关消息的载体。默认 thread 叫 `main`。TUI 重启后,
thread 历史仍然保留在本地 SQLite 中。

## Message

Message 由 envelope 和 body 组成。Envelope 包含 sender、recipients、room、
thread、subject、status、refs、tags、trace_id 等结构化字段;body 是不透明的
自由内容,原样保存和投递。

## Body

Body 可以是自然语言、Markdown、JSON、代码,或 agent 想发送的任何内容。
AgentMail 不解析、不裁剪、不改写、不模板化、不分类 body。

## Status

消息状态让协作过程可见:

- `queued`:已保存,尚未被主动投递。
- `delivered`:已交给 channel、bridge 或 inbox 投递路径。
- `seen`:接收方已查看。
- `claimed`:接收方正在处理。
- `replied`:已回复,但工作不一定完成。
- `resolved`:已完成。
- `cancelled` 或 `expired`:不再活跃。

## Inbox

Inbox 是某个 agent 在 mailbox 里的**per-recipient 视图**:`to_agents` 字段
含有这个 agent 的所有消息。Inbox 查询默认**排除 resolved/cancelled/expired**,
seen 是否包含是可选的。

CLI `agentmail inbox` 和 MCP `agentmail_inbox` **默认包含 seen 消息**;只有
传 `--unseen-only`(CLI)或 `include_seen: false`(MCP)才会过滤成
unseen-only。Delivery 与 watcher 路径内部使用 unseen-only,这样 adapter
只投递处于 `queued`/`delivered` 的待处理工作。

Inbox 是**派生视图**,不是单独的存储 — 每条消息只在 room 内存在一份,
按 envelope 中的 `to_agents` 浮现到对应 agent 的 inbox 里。

## Scope Claim

Scope claim 是轻量的路径占用提示,用来降低两个 agent 同时改同一批文件的
概率。它**不是强锁**:编辑前 claim,完成后 release。

## Artifact

Artifact 是对文件、diff、日志、截图或笔记的引用。长输出建议注册成 artifact,
而不是整段粘到消息 body 里。

## Timeline

Timeline 是 room 里**只追加(append-only)**的事件日志,记录每次状态变化:
agent 加入、message send/deliver/seen/claimed/replied/resolved、scope claim
与 release、artifact 注册、room 状态切换等。Timeline 可以通过
`agentmail_timeline`(MCP)或 `agentmail timeline`(CLI)查询,**是需要回溯
协作时间线时的真相源**;它跟 mailbox 本身一样,跨 TUI 重启都不会丢。

## Channel

Channel 是 Claude Code 的主动投递路径。AgentMail MCP server 会把新消息作为
Claude channel event 推入正在运行的 Claude Code 会话,Claude 在对话流里就能
直接看到。

## Bridge

Bridge 是面向**没有 channel 注入能力**的 agent runtime 的传输适配器。当前
实现的 bridge 面向 Codex App Server 和 Remote TUI。

## Discovery Notice

`agentmail start` 在加入房间时会向已上线的 peer 发送一条**去重的发现通知**
(discovery notice),让对方知道又有一个 agent 进入了 room。这只是一条普通
AgentMail 消息,可以用 `--no-announce` 关闭。
