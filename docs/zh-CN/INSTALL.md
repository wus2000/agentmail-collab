# 安装 AgentMail Collab

本指南从一份干净的源码 checkout 开始,把 AgentMail 装好,让 Claude Code 和
Codex 在日常项目里能够协作。

## 速览

AgentMail 有两种**完全不同**的状态:

- **工具(tool)可以全局装一次**:`agentmail` CLI、Claude Code 插件、Codex
  插件都可以装在 user/global 的插件位置。
- **协作数据(data)按项目隔离**:每个项目用自己的
  `<project>/.agentmail/agentmail.db`、bridge 状态、日志。

**不要在 shell 启动文件(`~/.zshrc`、`~/.bashrc` 等)里全局 export
`AGENTMAIL_DB=$HOME/.agentmail/agentmail.db`**。这样会让不同项目共用一个
room namespace 和同一份消息历史,几乎肯定不是你想要的。如果确实需要显式
指定数据库,只在某个 shell/项目里 export `AGENTMAIL_DB`。

## 前置要求

- Git。
- Python 3.10 或更新版本(`python3` 可用)。
- 已安装并登录 Claude Code。
- 已安装并登录 Codex。
- macOS 或 Linux 是当前测试最充分的本地工作流;Windows 建议先用 WSL。

## 拉取源码

克隆仓库并进入 AgentMail 仓库根目录:

```bash
git clone https://github.com/wus2000/agentmail-collab agentmail-collab
cd agentmail-collab
```

安装前可以先跑一遍完整的本地验证:

```bash
./scripts/validate.sh
```

该脚本会检查 Python 测试、JSON manifest、vendor 漂移、插件打包假设。

## 安装 CLI

从当前 checkout 安装 `agentmail` 命令:

```bash
python3 -m pip install -e .
agentmail --help
```

这会安装到你**当前激活的 Python 环境**。如果你平时用 `--user`、`pipx`、
`uv tool` 或项目 venv 来装开发工具,按你机器上的等价做法即可。关键是
`agentmail` 能在 `PATH` 里被找到。

发布到 package index 之后,非 editable 形式将是:

```bash
python3 -m pip install agentmail-collab
```

在那之前,使用 editable 的源码 checkout。

## 安装 Claude Code 插件

把仓库根目录作为 Claude Code marketplace 做校验:

```bash
claude plugin validate .
```

**跨项目长期使用推荐 user scope**:

```bash
claude plugin marketplace add "$(pwd)" --scope user
claude plugin install agentmail@agentmail-collab --scope user
```

Claude Code 支持 `user`、`project`、`local` 三种插件 scope:

- `user`:常规全局安装(推荐)
- `project`:仓库声明插件给该项目用
- `local`:你正在开发或测试这份 checkout

本地开发模式安装:

```bash
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-collab --scope local
```

如果 Claude Code 已经在运行,reload 一下插件:

```text
/reload-plugins
```

本地插件的 Claude channel 投递目前还是 research preview。要让 AgentMail
的消息能推到正在运行的 Claude Code 会话,启动 Claude Code 时加 channel
flag:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

## 安装 Codex 插件

把同一个仓库根目录加到 Codex 插件 marketplace:

```bash
codex plugin marketplace add "$(pwd)"
```

重启 Codex,打开 `/plugins`,选 `AgentMail Collab`,安装 `agentmail`。

Codex 的 marketplace 命令支持本地 marketplace 根目录、Git URL 和
`owner/repo[@ref]` 来源。如果你要做"个人/全局"安装,把 Codex 指向一个
稳定的本地 checkout 路径或已发布的 Git 仓库,后续 pull 完之后在
`/plugins` 里重装/更新插件。

## 在项目里使用 AgentMail

切到你真正想让 Claude Code 和 Codex 协作的项目目录:

```bash
cd /path/to/your-project
```

**第一个 join 房间的 agent 就会创建该房间**。Claude Code 不必先 join,
Codex 也可以先创建房间,或两边同时 join 已有房间。本指南用 `ecommerce`
作 room、`claude` 作 Claude agent 名、`codex` 作 Codex agent 名,但这些
名字没有任何特殊含义,你可以自由取名。

从项目目录用 channel flag 启动 Claude Code:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

在 Claude Code 里 join 房间:

```text
/agentmail:start ecommerce claude
```

slash 命令格式是:

```text
/agentmail:start <room> <agent>
```

如果你只想让普通 Codex TUI 显式地操作 mailbox,告诉 Codex:

```text
Use @agentmail. Join room ecommerce as codex, list peers, and check my inbox.
```

如果纯 CLI 起步,两边都可以直接 join:

```bash
agentmail join --room ecommerce --agent codex --kind codex --workspace "$PWD" --announce
agentmail join --room ecommerce --agent claude --kind claude --workspace "$PWD" --announce
```

带 `--workspace` 的 CLI 命令默认是 `.`,所以从项目根目录跑就行,或者
显式传 `--workspace /path/to/your-project`。不暴露 `--workspace` 的命令
则用 cwd、`--db` 或 `AGENTMAIL_DB` 来定位项目数据库。

## 项目内的主动唤醒

启用 channel flag 后,Claude Code 可以通过 Claude channel 主动收到
AgentMail 消息。Codex 对已经打开的普通 TUI **没有**等价的注入入口,
所以 AgentMail 用 Codex App Server 加 Remote TUI 模式来实现 Claude →
Codex 的主动唤醒。

推荐的 Codex 主动唤醒启动器:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

通过同一个唤醒通路恢复最近一次会话:

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

启动器会:join 房间、为 spawn 出来的 Codex 进程设置 `AGENTMAIL_DB` 和
`AGENTMAIL_WORKSPACE`、启动 `codex app-server`、启动 AgentMail bridge
loop,然后打开 `codex --remote ...`。

启动类命令会向已经在线的 peer 发一条**去重的发现通知**(discovery
notice),让对端 TUI 知道有新 peer 加入。需要"安静"启动时加
`--no-announce`。

如果你已经开了一个普通 Codex TUI,可以让它跑:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

`bootstrap-codex` 会打开一个新的 AgentMail-aware Codex Remote TUI 窗口。
后续主动唤醒协作请在新窗口里继续——**原来那个普通 Codex TUI 没法被
plugin/MCP 直接注入**。

恢复到最近一次 session:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD" --resume last
```

检查项目本地协作状态:

```bash
agentmail doctor --room ecommerce --workspace "$PWD"
```

## 数据放在哪里

| 路径 | 角色 | 范围 |
| --- | --- | --- |
| 包含 `agentmail` 的 Python 环境 | CLI 与 `agentmail-mcp` 入口 | 用户级/工具级 |
| Claude Code 插件 cache 或 user 安装 | Claude 插件载荷 + vendor runtime | 用户级/工具级 |
| Codex 插件安装/cache | Codex 插件载荷 + vendor runtime | 用户级/工具级 |
| `<project>/.agentmail/agentmail.db` | room、agent、thread、message、status、artifact、claim、timeline | **项目级数据** |
| `<project>/.agentmail/channel.json` | Claude channel 投递配置 | **项目级数据** |
| `<project>/.agentmail/codex-bridge/` | Codex bridge pid/状态文件 | **项目级数据** |
| `<project>/.agentmail/logs/` | 本地 AgentMail 日志 | **项目级数据** |

维护 AgentMail 本身时可以 commit 工具源码和插件包,但**绝对不要 commit
项目级的 `.agentmail/` 状态**。

## 显式数据库路径

AgentMail 解析项目数据库的顺序:

1. CLI 命令传的 `--db`
2. 已 export 的 `AGENTMAIL_DB`
3. CLI/MCP 调用里显式的 `workspace` 参数
4. `AGENTMAIL_WORKSPACE` / `CLAUDE_PROJECT_DIR` / `CODEX_WORKSPACE_ROOT`
5. 当前工作目录

做确定性的本地测试时,**只在某个项目的 shell 里**临时设:

```bash
cd /path/to/your-project
export AGENTMAIL_DB="$PWD/.agentmail/agentmail.db"
```

**不要**把这条 export 放进 `~/.zshrc`、`~/.bashrc` 或其他全局启动文件,
除非你**故意**要所有项目共享同一个 mailbox。

## Plugin Cache 防误判

全局插件安装时,Claude/Codex 可能从插件 cache 目录里启动 MCP server。
cache 是工具状态,**不是项目 workspace**。v0.1.0 起,如果 AgentMail 无法
推断真正的项目 workspace,会**拒绝**在 plugin cache 里创建数据库。

如果你看到这样的错误:

```text
AgentMail cannot infer the project workspace.
```

修复方法是给首次 join 调用传 `workspace`,或者在启动客户端前 export
项目专属环境变量:

```bash
export AGENTMAIL_WORKSPACE="$PWD"
```

Codex 的 AgentMail 管理启动器自动做这件事:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

如果旧版本曾经在 plugin cache 里创建过 DB,清理步骤见
[TROUBLESHOOTING.md](TROUBLESHOOTING.md)。

## 冒烟测试

让 Codex 发消息让 Claude 用 token 回复:

```text
Use @agentmail. Send Claude a message in room ecommerce asking it to reply with AGENTMAIL_SMOKE_ACK.
```

期望结果:

- Claude 在当前 Claude Code 会话里**自动**收到这条消息。
- Claude 用 `agentmail_reply` 回复。
- Codex 在自己的 AgentMail inbox 里看到回复。
- 如果 Codex 是用 `launch-codex` 或 `bootstrap-codex` 起的,Claude 发出的
  消息也能触发一次 Codex 的 `turn/start`。

也可以从 shell 直接看一眼房间状态:

```bash
agentmail status --room ecommerce
agentmail inbox --agent codex --room ecommerce
agentmail timeline --room ecommerce
```

## 更新已安装版本

源码安装的更新流程:

```bash
cd /path/to/agentmail-collab
git pull
python3 -m pip install -e .
python plugins/sync_vendor.py --check
./scripts/validate.sh
```

如果插件载荷有改动,从同一个 marketplace 重装或更新客户端插件:

```bash
claude plugin install agentmail@agentmail-collab --scope user
codex plugin marketplace add "$(pwd)"
```

然后重载/重启对应 TUI:

```text
/reload-plugins
```

Codex 这边重启,在 `/plugins` 里更新或重装 `AgentMail Collab`(如果 UI
还显示旧版本)。

## 注意事项

- AgentMail **默认不显示 macOS 系统通知**。
- Claude Code channel 仍处于 research preview,本地插件需要
  `--dangerously-load-development-channels` flag。
- 普通 Codex TUI **不能**被 plugin/MCP 直接注入消息;主动唤醒要用
  `launch-codex` 或 `bootstrap-codex`。
- 消息正文是自由内容,**按原样保存与投递**;只有 envelope 字段是结构化的。
