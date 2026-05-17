#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

python -m pip install -e . >/dev/null
python plugins/sync_vendor.py
python -m unittest discover -s tests -v
python -m py_compile *.py tests/*.py
python -m json.tool .claude-plugin/marketplace.json >/dev/null
python -m json.tool .agents/plugins/marketplace.json >/dev/null
python -m json.tool plugins/claude-marketplace/plugins/agentmail/.claude-plugin/plugin.json >/dev/null
python -m json.tool plugins/codex-marketplace/plugins/agentmail/.codex-plugin/plugin.json >/dev/null

test -x plugins/claude-marketplace/plugins/agentmail/bin/agentmail
test -x plugins/claude-marketplace/plugins/agentmail/bin/agentmail-mcp
test -x plugins/codex-marketplace/plugins/agentmail/bin/agentmail
test -x plugins/codex-marketplace/plugins/agentmail/bin/agentmail-mcp

if command -v claude >/dev/null 2>&1; then
  claude plugin validate .
else
  printf '%s\n' "warning: claude CLI not found; skipped Claude plugin validation" >&2
fi

find . \( -name __pycache__ -o -name '*.egg-info' \) -type d -prune -exec rm -rf {} +
