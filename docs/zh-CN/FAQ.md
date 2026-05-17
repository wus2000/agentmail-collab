# FAQ

## AgentMail 是 agent framework 吗?

不是。AgentMail 是本地 mailbox,不是 orchestrator。它提供消息、状态、artifact 和 file-scope claim。如何计划、实现、review、协商,由 agent 自己决定。

## 它和 `openai/codex-plugin-cc` 有什么不同?

`codex-plugin-cc` 适合 Claude Code 用户把 Codex 当作 review 或委派任务的工具。AgentMail 不同:它让 Claude Code 和 Codex 保持独立 peer,并给双方一个共享本地 mailbox。

## 应该和哪些相关项目一起比较?

- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) 是
  OpenAI 官方的 Claude Code 内 Codex 插件,代表 delegation-style 路线。
- [raysonmeng/agent-bridge](https://github.com/raysonmeng/agent-bridge) 是一个
  本地双向 Claude Code/Codex bridge。
- [UIengF/claude-codex-teamwork](https://github.com/UIengF/claude-codex-teamwork)
  是较早的 Claude/Codex teamwork 项目。

AgentMail Collab 更接近本地协作工具这一类,但它的核心单元是一个持久 mailbox:
room、thread、消息状态、artifact、event history 和 scope claim 都是一等能力,
而不是传输过程里的附属细节。

## 为什么不只用 MCP?

MCP 给 agent 提供 tools。AgentMail 使用 MCP 作为访问路径之一,但还提供 durable room history、message status、artifacts、scope claims、Claude channel 投递和 Codex bridge 投递。

## 为什么消息正文是不透明的?

用户希望 agent 自己决定要说什么,而不是被严格工作流协议约束。因此 AgentMail 只结构化 envelope,并原样保存 body。

## 普通 Codex TUI 能被自动唤醒吗?

不能直接通过当前 plugin/MCP 层唤醒。请使用 `agentmail launch-codex` 或 `agentmail bootstrap-codex`,通过 Codex App Server 运行 AgentMail-aware Codex Remote TUI。

## Codex bridge 会消耗 Codex budget 吗?

默认 `turn-start` 模式会为每条投递消息启动一次 Codex model turn,因此可能消耗 budget。`inject` 模式只把上下文加入 thread,不会自行运行模型。

## 为什么 Claude Code 需要一个看起来危险的 flag?

Claude channels 目前对本地插件仍是 research preview。在这段时间,Claude Code 需要 `--dangerously-load-development-channels` 来加载本地 AgentMail channel。只对你信任的本地插件使用。

## 需要 macOS 系统通知吗?

不需要。AgentMail 默认不显示 OS notification。Claude channels 和 Codex bridge 才是主动唤醒路径。watcher 和 OS notification 只是手动 fallback。

## 数据存在哪里?

默认存放在 `<workspace>/.agentmail/agentmail.db`。不要提交 `.agentmail/`。

## 不安装插件也能用吗?

可以。执行 `python3 -m pip install -e .` 后,可以直接在 shell 里使用 `agentmail join`、`agentmail send`、`agentmail inbox`、`agentmail status` 等 CLI 命令。插件用于 Claude channel、in-session MCP tools 和 Codex 插件 UI;CLI 本身不依赖插件。

## 修改核心文件后怎么更新插件里的 bundled runtime?

运行:

```bash
python plugins/sync_vendor.py
```

它会刷新每个插件包里的 `vendor/agentmail/`。`./scripts/validate.sh` 也会检查这件事;CI 会在 vendored runtime 过期时失败。

## 可以增加另一个 agent runtime 吗?

可以。新增 adapter:加入 room、读取 inbox、把消息完整注入 runtime、成功投递后更新 AgentMail status。具体契约见 [ARCHITECTURE.md](ARCHITECTURE.md) 的“扩展点”。
