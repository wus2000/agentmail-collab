# Release Checklist

Use this checklist before publishing AgentMail as a plugin repository.

The `agentmail/` directory is intended to become the standalone public plugin
repository root. Paths such as `.github/workflows/ci.yml`,
`.claude-plugin/marketplace.json`, and `.agents/plugins/marketplace.json` are
relative to `agentmail/`, not the parent development workspace.

## Source Hygiene

- Remove generated caches: `find . -name __pycache__ -type d -prune -exec rm -rf {} +`
- Run `python plugins/sync_vendor.py` after any core Python changes.
- Confirm the vendored plugin packages do not reference files outside the
  installed plugin root.
- Keep the Claude channel warning in install docs while channels are in
  research preview.

## Validation

```bash
./scripts/validate.sh
```

The script checks:

- Python unit tests.
- Python syntax.
- Claude marketplace validation, when `claude` is installed.
- Required Codex marketplace and plugin manifests.
- Required plugin wrapper scripts.

## Versioning

- Bump both plugin manifests:
  - `plugins/claude-marketplace/plugins/agentmail/.claude-plugin/plugin.json`
  - `plugins/codex-marketplace/plugins/agentmail/.codex-plugin/plugin.json`
- Keep root marketplace entries pointed at the released plugin directories.
- Tag releases after validation passes.

## Manual Smoke Test

1. Install the Claude marketplace from the repository root:

   ```bash
   claude plugin marketplace add "$(pwd)" --scope local
   claude plugin install agentmail@agentmail-collab --scope local
   ```

2. Install the Codex marketplace from the repository root:

   ```bash
   codex plugin marketplace add "$(pwd)"
   ```

3. Start Claude with channel support:

   ```bash
   claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
   ```

4. Join the same room from Claude and Codex, then send a message both ways.

## Publishing Notes

For Claude Code GitHub distribution, the repository root contains
`.claude-plugin/marketplace.json`. For Codex local marketplace distribution, the
repository root contains `.agents/plugins/marketplace.json`.
