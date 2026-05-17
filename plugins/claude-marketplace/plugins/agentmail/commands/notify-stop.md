---
description: Stop AgentMail background inbox notifications
argument-hint: "[room] [agent-name]"
allowed-tools: Bash
---

Stop a background AgentMail watcher for this Claude Code session.

Use `$ARGUMENTS` as optional positional input:

- first token: room name, default `default`
- second token: agent name, default `claude`

Run:

```bash
room="$(printf '%s\n' "$ARGUMENTS" | awk '{print $1}')"
agent="$(printf '%s\n' "$ARGUMENTS" | awk '{print $2}')"
room="${room:-default}"
agent="${agent:-claude}"
workspace="${CLAUDE_PROJECT_DIR:-$PWD}"
"${CLAUDE_PLUGIN_ROOT}/bin/agentmail" --json notify-stop \
  --agent "$agent" \
  --room "$room" \
  --workspace "$workspace"
```

Report whether a watcher was stopped.
