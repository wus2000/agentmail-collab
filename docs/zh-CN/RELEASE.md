# 发布清单

发布 AgentMail 插件仓库前使用这份清单。

`agentmail/` 目录应该成为独立公开插件仓库的根目录。`.github/workflows/ci.yml`、
`.claude-plugin/marketplace.json`、`.agents/plugins/marketplace.json` 等路径都相对于
`agentmail/`,不是父级开发 workspace。

## Source Hygiene

- 移除生成缓存:

  ```bash
  find . -name __pycache__ -type d -prune -exec rm -rf {} +
  ```

- 改动核心 Python 文件后运行 `python plugins/sync_vendor.py`。
- 确认 vendored plugin package 不引用安装后 plugin root 之外的文件。
- 在 Claude channels 仍是 research preview 时,保留 install docs 中的 warning。

## 验证

```bash
./scripts/validate.sh
```

这个脚本检查:

- Python unit tests
- Python syntax
- Claude marketplace validation(如果安装了 `claude`)
- 必需的 Codex marketplace 和 plugin manifests
- 必需的 plugin wrapper scripts

## 版本

- 同步 bump 两个 plugin manifest:
  - `plugins/claude-marketplace/plugins/agentmail/.claude-plugin/plugin.json`
  - `plugins/codex-marketplace/plugins/agentmail/.codex-plugin/plugin.json`
- 保持 root marketplace entries 指向已发布的 plugin directories。
- validation 通过后再打 tag。

## 手动冒烟测试

1. 从仓库根目录安装 Claude marketplace:

   ```bash
   claude plugin marketplace add "$(pwd)" --scope local
   claude plugin install agentmail@agentmail-collab --scope local
   ```

2. 从仓库根目录安装 Codex marketplace:

   ```bash
   codex plugin marketplace add "$(pwd)"
   ```

3. 启动带 channel support 的 Claude:

   ```bash
   claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
   ```

4. Claude 和 Codex 加入同一个 room,然后双向发送消息。

## 发布说明

Claude Code 的 GitHub 分发入口是仓库根目录的 `.claude-plugin/marketplace.json`。
Codex local marketplace 分发入口是仓库根目录的 `.agents/plugins/marketplace.json`。
