# AgentMail Collab 中文文档

这里是中文文档入口。中文文档覆盖安装、核心概念、架构、主动投递、
Codex bridge、CLI/MCP 参考、故障排查、FAQ、测试和发布清单。

## 推荐阅读顺序

1. [INSTALL.md](INSTALL.md):安装 Claude Code plugin、Codex plugin 和 CLI。
2. [CONCEPTS.md](CONCEPTS.md):理解 room、thread、message、status、claim、
   channel、bridge 等核心术语。
3. [ARCHITECTURE.md](ARCHITECTURE.md):理解 mailbox core、transport adapters、
   部署形态和模块地图。
4. [CHANNELS.md](CHANNELS.md):理解 Claude channel 和 Codex bridge 的主动投递语义。
5. [CODEX_BRIDGE.md](CODEX_BRIDGE.md):配置和调试 Codex App Server bridge。
6. [TROUBLESHOOTING.md](TROUBLESHOOTING.md):排查 DB、channel、bridge、插件缓存问题。

## 参考文档

- [CLI_REFERENCE.md](CLI_REFERENCE.md):`agentmail` 命令速查。
- [MCP_REFERENCE.md](MCP_REFERENCE.md):`agentmail_*` MCP 工具速查。
- [FAQ.md](FAQ.md):定位、预算、普通 Codex TUI、OS notification 等常见问题。
- [TESTING.md](TESTING.md):自动化测试和实际协作测试。
- [RELEASE.md](RELEASE.md):发布前检查清单。
- [../../README.zh-CN.md](../../README.zh-CN.md):中文 landing page。
- [../../SECURITY.zh-CN.md](../../SECURITY.zh-CN.md):中文安全说明。

## 常用命令速查

启动 Claude Code 并打开 development channel:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

在 Claude Code 里加入房间:

```text
/agentmail:start ecommerce claude
```

启动可被主动唤醒的 Codex Remote TUI:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

恢复最近一次 Codex 会话:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

自检本地协作状态:

```bash
agentmail doctor --room ecommerce --workspace "$PWD"
```
