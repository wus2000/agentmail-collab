#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

printf '%s\n' "==> Installing editable package"
python -m pip install -e . >/dev/null

printf '%s\n' "==> Checking vendored plugin runtime"
python plugins/sync_vendor.py --check

printf '%s\n' "==> Running unit tests"
python -m unittest discover -s tests -v

printf '%s\n' "==> Compiling Python sources"
python -m py_compile *.py tests/*.py

printf '%s\n' "==> Validating JSON manifests"
json_files=(
  ".claude-plugin/marketplace.json"
  ".agents/plugins/marketplace.json"
  "plugins/claude-marketplace/.claude-plugin/marketplace.json"
  "plugins/codex-marketplace/.agents/plugins/marketplace.json"
  "plugins/claude-marketplace/plugins/agentmail/.claude-plugin/plugin.json"
  "plugins/codex-marketplace/plugins/agentmail/.codex-plugin/plugin.json"
  "plugins/claude-marketplace/plugins/agentmail/.mcp.json"
  "plugins/codex-marketplace/plugins/agentmail/.mcp.json"
)

for json_file in "${json_files[@]}"; do
  python -m json.tool "${json_file}" >/dev/null
done

test -x plugins/claude-marketplace/plugins/agentmail/bin/agentmail
test -x plugins/claude-marketplace/plugins/agentmail/bin/agentmail-mcp
test -x plugins/codex-marketplace/plugins/agentmail/bin/agentmail
test -x plugins/codex-marketplace/plugins/agentmail/bin/agentmail-mcp

if command -v claude >/dev/null 2>&1; then
  printf '%s\n' "==> Validating Claude plugin marketplaces"
  claude plugin validate .
  claude plugin validate plugins/claude-marketplace
else
  printf '%s\n' "warning: claude CLI not found; skipped Claude plugin validation" >&2
fi

printf '%s\n' "==> Cleaning generated Python caches"
find . \( -name __pycache__ -o -name '*.egg-info' \) -type d -prune -exec rm -rf {} +

printf '%s\n' "==> Validation complete"
