#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

install_claude=1
install_codex=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude-only)
      install_codex=0
      ;;
    --codex-only)
      install_claude=0
      ;;
    -h|--help)
      cat <<'EOF'
Usage: scripts/install-local.sh [--claude-only|--codex-only]

Install the local AgentMail marketplace into Claude Code and/or Codex.
Run from anywhere inside the checkout.
EOF
      exit 0
      ;;
    *)
      printf 'unknown option: %s\n' "$1" >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "${install_claude}" -eq 1 ]]; then
  command -v claude >/dev/null 2>&1 || {
    printf '%s\n' "claude CLI not found" >&2
    exit 1
  }
  claude plugin validate "${ROOT}"
  claude plugin marketplace add "${ROOT}" --scope local
  claude plugin install agentmail@agentmail-local --scope local
fi

if [[ "${install_codex}" -eq 1 ]]; then
  command -v codex >/dev/null 2>&1 || {
    printf '%s\n' "codex CLI not found" >&2
    exit 1
  }
  if ! codex plugin marketplace add "${ROOT}"; then
    cat >&2 <<EOF
Codex marketplace agentmail-local is already configured from a different source.
Remove it and add this checkout explicitly:

  codex plugin marketplace remove agentmail-local
  codex plugin marketplace add "${ROOT}"
EOF
    exit 1
  fi
fi

cat <<EOF
AgentMail local marketplace installed.

CLI command, if not already installed:
  python3 -m pip install -e "${ROOT}"

Claude channel startup:
  claude --dangerously-load-development-channels plugin:agentmail@agentmail-local

Claude room command:
  /agentmail:start ecommerce claude

Codex active-wakeup startup:
  agentmail launch-codex --room ecommerce --workspace "\$PWD"

Codex ordinary room prompt:
  Use @agentmail. Join room ecommerce as codex, list peers, and check my inbox.
EOF
