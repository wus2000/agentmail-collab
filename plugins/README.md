# AgentMail Plugin Packages

This directory contains the self-contained plugin payloads for Claude Code and
Codex. It is packaging infrastructure, not the main install guide.

Use the top-level docs as the single source of truth:

- `README.md` for the quick start.
- `docs/INSTALL.md` for full installation and upgrade steps.
- `docs/CODEX_BRIDGE.md` for Codex Remote TUI active wakeups.

The supported marketplace entrypoints live at the repository root:

- `agentmail/.claude-plugin/marketplace.json`
- `agentmail/.agents/plugins/marketplace.json`

The nested marketplace directories mirror installable payloads for local
validation and distribution testing. Do not add both the root marketplace and a
nested `plugins/*-marketplace` directory to the same client; the manifests
currently share the local marketplace name and can collide.

## Layout

```text
plugins/
  codex-marketplace/
    .agents/plugins/marketplace.json
    plugins/agentmail/
      .codex-plugin/plugin.json
      .mcp.json
      skills/agentmail/SKILL.md
      bin/agentmail
      bin/agentmail-mcp
      vendor/agentmail/
  claude-marketplace/
    .claude-plugin/marketplace.json
    plugins/agentmail/
      .claude-plugin/plugin.json
      .mcp.json
      skills/agentmail/SKILL.md
      commands/start.md
      commands/status.md
      bin/agentmail
      bin/agentmail-mcp
      vendor/agentmail/
```

Each plugin bundles AgentMail under `vendor/agentmail/` so installed plugins do
not reference source files outside the client plugin cache.

## Rebuild Bundled Runtime

Run this after changing core Python files:

```bash
python plugins/sync_vendor.py
```

The release validation script runs the vendor sync and plugin checks:

```bash
./scripts/validate.sh
```
