# 测试 AgentMail

## 自动化测试

从 `agentmail/` 目录运行:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m py_compile *.py tests/*.py
claude plugin validate .
```

如果没有安装 `claude`, `scripts/validate.sh` 会跳过 Claude validation。

## 插件包测试

重建 vendored code:

```bash
python plugins/sync_vendor.py
```

校验 Claude marketplace:

```bash
claude plugin validate .
```

检查 Codex marketplace JSON:

```bash
python -m json.tool .agents/plugins/marketplace.json >/dev/null
python -m json.tool plugins/codex-marketplace/plugins/agentmail/.codex-plugin/plugin.json >/dev/null
```

## 实际协作测试

1. 启动开启 AgentMail channel 的 Claude Code。
2. 运行 `/agentmail:start ecommerce claude`。
3. 启动已安装 AgentMail plugin 的 Codex。
4. 让 Codex 以 `codex` 身份加入 `ecommerce`。
5. 从 Codex 向 Claude 发送 free-form message。
6. 确认 Claude 不需要手动转发就能回复。

有用的断言:

- 状态流为 `message.sent -> message.delivered -> message.seen -> message.replied`。
- reply 保留原消息的 `trace_id`。
- 包含 Markdown、JSON-like text 和 angle brackets 的 message body 仍然完整。

## Codex Bridge 冒烟测试

通过实验性 bridge 启动 Codex:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

然后从 Claude 向 Codex 发消息。期望结果:

- `agentmail codex-bridge status` 显示 bridge 正在运行。
- bridge 调用 Codex App Server 后,消息从 `queued` 变成 `delivered`。
- Codex 收到一个新 turn,内容包含 AgentMail envelope 和位于
  `---BEGIN_AGENTMAIL_BODY---` / `---END_AGENTMAIL_BODY---` 之间的 exact body。
