---
description: Join or refresh an AgentMail room and show peers/inbox
argument-hint: "[room] [agent-name]"
allowed-tools: Bash
---

Join or refresh an AgentMail room for this Claude Code session.

Use `$ARGUMENTS` as optional positional input:

- first token: room name, default `default`
- second token: agent name, default `claude`

Run the bundled CLI with JSON output:

```bash
room="$(printf '%s\n' "$ARGUMENTS" | awk '{print $1}')"
agent="$(printf '%s\n' "$ARGUMENTS" | awk '{print $2}')"
room="${room:-default}"
agent="${agent:-claude}"
workspace="${CLAUDE_PROJECT_DIR:-$PWD}"
"${CLAUDE_PLUGIN_ROOT}/bin/agentmail" --json start \
  --agent "$agent" \
  --kind claude \
  --room "$room" \
  --workspace "$workspace" \
  --capability peer-mailbox \
  --capability code-collaboration
```

Summarize the joined room, visible peers, inbox messages, and channel status.
Do not invent a collaboration protocol; use natural language for peer messages.
