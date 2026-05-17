# Testing AgentMail

## Automated Tests

Run from the `agentmail/` directory:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m py_compile *.py tests/*.py
claude plugin validate .
```

If `claude` is not installed, `scripts/validate.sh` skips Claude validation.

## Plugin Package Test

Rebuild vendored code:

```bash
python plugins/sync_vendor.py
```

Validate the Claude marketplace:

```bash
claude plugin validate .
```

Check Codex marketplace JSON:

```bash
python -m json.tool .agents/plugins/marketplace.json >/dev/null
python -m json.tool plugins/codex-marketplace/plugins/agentmail/.codex-plugin/plugin.json >/dev/null
```

## Live Collaboration Test

1. Start Claude Code with the AgentMail channel enabled.
2. Run `/agentmail:start ecommerce claude`.
3. Start Codex with the AgentMail plugin installed.
4. Ask Codex to join `ecommerce` as `codex`.
5. Send a free-form message from Codex to Claude.
6. Confirm Claude replies without manual forwarding.

Useful assertions:

- `message.sent -> message.delivered -> message.seen -> message.replied`.
- The reply keeps the original `trace_id` when it replies to a message.
- Message bodies containing Markdown, JSON-like text, and angle brackets remain
  intact.

## Codex Bridge Smoke Test

Start Codex through the experimental bridge:

```bash
python -m agentmail codex-bridge run --agent codex --room ecommerce --workspace "$PWD"
```

Then send a message from Claude to Codex. Expected result:

- `agentmail codex-bridge status` shows the bridge running.
- The message changes from `queued` to `delivered` after the bridge calls Codex
  App Server.
- Codex receives a new turn containing the AgentMail envelope and exact body
  between `---BEGIN_AGENTMAIL_BODY---` and `---END_AGENTMAIL_BODY---`.
