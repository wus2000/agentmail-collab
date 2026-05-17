---
description: Show AgentMail peers, inbox, and recent room timeline
argument-hint: "[room] [agent-name]"
allowed-tools: Bash
---

Show the current AgentMail state for this Claude Code session.

Use `$ARGUMENTS` as optional positional input:

- first token: room name, default `default`
- second token: agent name, default `claude`

Run:

```bash
room="$(printf '%s\n' "$ARGUMENTS" | awk '{print $1}')"
agent="$(printf '%s\n' "$ARGUMENTS" | awk '{print $2}')"
room="${room:-default}"
agent="${agent:-claude}"
"${CLAUDE_PLUGIN_ROOT}/bin/agentmail" --json status --agent "$agent" --room "$room"
"${CLAUDE_PLUGIN_ROOT}/bin/agentmail" --json notify-status --agent "$agent" --room "$room"
"${CLAUDE_PLUGIN_ROOT}/bin/agentmail" --json timeline --room "$room" --limit 20
```

Summarize only the state that matters for the next action.
