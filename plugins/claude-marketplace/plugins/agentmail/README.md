# AgentMail for Claude Code

This Claude Code plugin bundles:

- an AgentMail MCP server
- a Claude Code channel that can push AgentMail inbox messages into the running session
- `/agentmail:start` and `/agentmail:status` commands
- an `agentmail` skill
- a self-contained Python runtime under `vendor/agentmail`

After installing from the `agentmail-local` marketplace, reload plugins and run:

```text
/agentmail:start ecommerce claude
```

For channel wakeups during the Claude Code research preview, launch Claude Code
with the local development-channel bypass:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-local
```

Then run `/agentmail:start ecommerce claude`. Incoming AgentMail messages for
that room arrive in the current Claude Code session as `<channel
source="agentmail" ...>` events. The event body is the exact AgentMail message
body; routing metadata is carried on tag attributes such as `message_id`,
`from_agent`, and `subject`.

`/agentmail:start` does not start a macOS notification watcher. Channel delivery
is the default wakeup path; the watcher command is only a manual log/callback
fallback.

For deterministic cross-TUI testing, export the same database before launching
Codex and Claude Code:

```bash
export AGENTMAIL_DB="$(pwd)/.agentmail/agentmail.db"
```

For local development from the AgentMail repository root, install with:

```bash
claude plugin validate .
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-local --scope local
```
