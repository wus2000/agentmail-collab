---
description: Show AgentMail background watcher status
argument-hint: "[room] [agent-name]"
allowed-tools: Bash
---

Show the background AgentMail watcher status for this Claude Code session.
This watcher is only a log/callback fallback; Claude channel delivery is the
primary wakeup path.

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
"${CLAUDE_PLUGIN_ROOT}/bin/agentmail" --json notify-status \
  --agent "$agent" \
  --room "$room" \
  --workspace "$workspace"
```

Report whether the watcher is running and show its log path.
