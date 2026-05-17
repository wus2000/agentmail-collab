# AgentMail Collab

**AgentMail Collab 是一个本地 peer mailbox,不是 agent 编排框架。**

现有的 Claude/Codex 桥接插件大多把一个 CLI 变成另一个 CLI 的工具;AgentMail
不这么做。它让 Claude Code 和 Codex 保持各自独立,通过一个共享的本地 SQLite
mailbox 在同一个 workspace、同一个 room、同一个 thread 里像同事一样交换
opaque 消息,使用 Claude Code channel 和 Codex App Server bridge 作为传输适配器。

AgentMail Collab 与 PyPI 上的 `agentmail`(Agentmail 这家公司的托管 API)无关。
本项目以 `agentmail-collab` 名义发布,以避免混淆。

[English README](README.md)

## 你会得到什么

- 一个面向 Claude Code、Codex 和其他 coding agent 的本地持久 mailbox。
- 基于 workspace SQLite 的 room、thread、消息状态、artifact、event history
  和文件范围 claim。
- 通过 Claude channel 主动唤醒正在运行的 Claude Code 会话。
- 通过 Codex App Server 加 Remote TUI 实验性地把 Claude 消息主动推入 Codex。
- 同时提供 Claude Code plugin、Codex plugin,以及一个普通的 `agentmail` CLI
  用于脚本和本地调试。

AgentMail 不解析消息正文。除了 sender、recipient、room、thread、status、
refs、tags 这类 envelope 字段之外,agent 发出的正文会原样保存和投递。

## 前置要求

- 已安装并登录 Claude Code。
- 已安装并登录 Codex。
- Python 3.10 或更新版本。
- 目前测试最充分的本地工作流环境是 macOS 和 Linux;Windows 建议先用 WSL。

## 与同类项目的区别

- **vs `openai/codex-plugin-cc`**:它让 Claude Code 把 Codex 当作工具来调用,
  适合 review 或委派任务;AgentMail 把两边都当作自主的 peer。
- **vs `cc-codex-bridge` 等社区桥接**:它们做的是单向配置同步;AgentMail
  不同步配置,只负责传递消息。
- **vs Google A2A 等网络协议**:A2A 是跨网络的强协议;AgentMail 是本地、
  轻量、不强制协议的 mailbox。
- **vs PyPI 上的 hosted `agentmail`**:那是 Agentmail 公司的托管 API;
  本项目是本地 peer mailbox,与之无关。

## 相关项目与参考

AgentMail Collab 的设计参考并对比了已有的 Claude/Codex 协作工具和桥接方案:

- [raysonmeng/agent-bridge](https://github.com/raysonmeng/agent-bridge):
  一个本地双向 Claude Code/Codex bridge。AgentMail Collab 选择 mailbox-first
  路线,重点放在持久 thread、消息状态、artifact 和 scope claim。
- [UIengF/claude-codex-teamwork](https://github.com/UIengF/claude-codex-teamwork):
  一个 Claude/Codex teamwork 项目,帮助验证了本地 peer-agent 工作流的实际需求。
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc):
  OpenAI 官方的 Claude Code 内 Codex 插件,更适合 delegation-style 工作流;
  AgentMail Collab 则让两个 CLI 都保持自主,以 peer 方式协作。

## 从源码快速开始

把 AgentMail Collab CLI 和插件 marketplace 全局装一次,然后从任意项目使用。**工具
可以全局装,协作数据按 workspace 留在 `<project>/.agentmail/` 下面**。

克隆仓库:

```bash
git clone https://github.com/wus2000/agentmail-collab agentmail-collab
cd agentmail-collab
```

从这个 checkout 安装 CLI:

```bash
python3 -m pip install -e .
agentmail --help
```

从仓库根目录安装 Claude Code 插件 marketplace。**推荐 user scope**,跨项目
都生效:

```bash
claude plugin validate .
claude plugin marketplace add "$(pwd)" --scope user
claude plugin install agentmail@agentmail-collab --scope user
```

如果你只想给这一个项目临时装(开发模式),用 `--scope local` 即可。

从同一个仓库根目录安装 Codex 插件 marketplace:

```bash
codex plugin marketplace add "$(pwd)"
```

重启 Codex,打开 `/plugins`,选 `AgentMail Collab`,安装 `agentmail`。

切到你真正要让 Claude Code 和 Codex 协作的项目目录:

```bash
cd /path/to/your-project
```

Claude channel 当前是 research preview,启动 Claude Code 时加 channel flag:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

在 Claude Code 里加入房间。**room 和 agent 名是你自己定的**,第一个 join
的 agent 就会创建房间:

```text
/agentmail:start <room> <agent>
```

例如:

```text
/agentmail:start ecommerce claude
```

如果你只需要让普通 Codex TUI 显式访问 mailbox,告诉 Codex:

```text
Use @agentmail. Join room ecommerce as codex, list peers, and check my inbox.
```

要让 Claude 发的消息主动唤醒 Codex,在项目目录用 AgentMail 启动 Codex:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

恢复最近一次 Codex 会话:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

如果你已经在普通 Codex TUI 里,让它启动一个新的 AgentMail-aware Remote TUI:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

**原来的普通 Codex TUI 没法被 plugin/MCP 直接注入**,主动唤醒协作请在新的
Remote TUI 里继续。

**不要**在 shell 启动文件(`~/.zshrc`、`~/.bashrc` 等)里全局 export
`AGENTMAIL_DB=$HOME/.agentmail/agentmail.db`。让数据按项目隔离;如果确实要
显式指定,只在某个项目的 shell 里临时 export。完整的全局安装流程见
[中文安装指南](docs/zh-CN/INSTALL.md)。

## 常见工作流

1. 在同一个项目里打开 Claude Code 和 Codex。
2. 用 development channel 启动 Claude Code,并执行 `/agentmail:start <room> claude`。
3. 如果需要 Codex 被 Claude 主动唤醒,用
   `agentmail launch-codex --room <room> --workspace "$PWD"` 启动 Codex。
4. 让两个 agent 协作:发自然语言消息、在编辑前 claim 文件路径、把长日志或
   diff 注册成 artifact。
5. 链路异常时跑一遍 `agentmail doctor --room <room> --workspace "$PWD"`。

## 稳定与实验

本版本中相对稳定的部分:

- SQLite mailbox、room、thread、消息状态、artifact、scope claim。
- CLI 命令和 stdio MCP 工具。
- Claude Code plugin 和 Claude channel 投递。
- Codex plugin 中显式的 mailbox 使用。

实验性部分:

- Codex App Server bridge,也就是 `agentmail launch-codex`、
  `agentmail bootstrap-codex` 和 `agentmail codex-bridge ...`。它依赖
  Codex App Server 与 Remote TUI API,后续版本可能调整。

## 文档

- [中文文档入口](docs/zh-CN/README.md)
- [中文安装指南](docs/zh-CN/INSTALL.md)
- [中文概念说明](docs/zh-CN/CONCEPTS.md)
- [中文架构与模块说明](docs/zh-CN/ARCHITECTURE.md)
- [中文主动投递说明](docs/zh-CN/CHANNELS.md)
- [中文 Codex bridge 说明](docs/zh-CN/CODEX_BRIDGE.md)
- [中文 CLI 参考](docs/zh-CN/CLI_REFERENCE.md)
- [中文 MCP 工具参考](docs/zh-CN/MCP_REFERENCE.md)
- [中文故障排查](docs/zh-CN/TROUBLESHOOTING.md)
- [中文 FAQ](docs/zh-CN/FAQ.md)
- [中文测试说明](docs/zh-CN/TESTING.md)
- [中文发布清单](docs/zh-CN/RELEASE.md)

## 仓库结构

```text
agentmail/
  .claude-plugin/marketplace.json  Claude Code marketplace 入口
  .agents/plugins/marketplace.json Codex marketplace 入口
  pyproject.toml                   Python 包元数据
  *.py                             核心包模块
  docs/                            用户、运维、维护者文档
  skills/                          Claude / Codex 用的 skill 指南源
  plugins/                         自包含的 Claude Code 与 Codex 插件载荷
  scripts/                         本地安装与验证脚本
  tests/                           单元和集成测试
```

AgentMail 故意**不**附带插件级的 `agents/` 定义。agent 行为是在消息正文里
谈出来的,不是打包成固定 persona。

## 开发

发布或开 PR 前跑一遍验证脚本:

```bash
./scripts/validate.sh
```

改了核心 Python 模块之后跑:

```bash
python plugins/sync_vendor.py
```

插件载荷是自包含的,vendor 了 Python runtime,这样安装出去的插件不会引用
客户端 cache 之外的文件。

## 安全提示

AgentMail 虽然是本地工具,但 peer message 仍然是不可信输入。在执行 shell
命令或破坏性改动前要照常审查。`.agentmail/` 目录里的 SQLite 数据库可能含
项目上下文、文件路径和 agent 消息,**不要提交到 git**。

Claude channel 当前依赖:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

只对你信任的本地插件使用这个 flag。完整本地安全模型见
[SECURITY.zh-CN.md](SECURITY.zh-CN.md)。
