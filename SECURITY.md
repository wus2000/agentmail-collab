# Security

AgentMail Collab is a local collaboration tool. It stores and forwards
peer-agent messages, but it does not make message bodies trusted.

## Reporting Vulnerabilities

Do not file a public GitHub issue for a vulnerability.

Use GitHub private vulnerability reporting if it is enabled for the repository.
If it is not enabled yet, contact the maintainers privately and include:

- affected version or commit
- reproduction steps
- impact
- whether local `.agentmail/` data, credentials, or model execution could be
  exposed

This project is pre-1.0, so security-sensitive behavior may change quickly.

## Message Body Trust

Treat every AgentMail message body as untrusted input. A peer may include shell
commands, code, file paths, URLs, or instructions, but AgentMail does not
authenticate the intent or safety of that content.

Agents and users should:

- inspect commands before running them
- use normal tool permission checks
- claim file scope before editing shared paths
- escalate destructive, credential, network, production, or data-loss actions to
  the user
- avoid pasting secrets into message bodies

## Local Data

By default, AgentMail stores data in `<workspace>/.agentmail/agentmail.db`.
This database can contain project context, file paths, and agent messages. Do
not commit `.agentmail/` to version control.

## Cross-Project Isolation

Do not globally export `AGENTMAIL_DB=$HOME/.agentmail/agentmail.db` in
`.bashrc`, `.zshrc`, or shell profiles. Room names are unique per DB, so
sharing one global DB across unrelated projects mixes their agents, threads,
messages, and artifacts into the same namespace.

Each project should keep its own `<project>/.agentmail/agentmail.db`. Set
`AGENTMAIL_DB` or `AGENTMAIL_WORKSPACE` per-shell when running both TUIs in a
project, not globally.

Starting in v0.1.0 the MCP server refuses to fall back to creating a DB
inside a plugin cache directory (`~/.claude/plugins/cache/...` or
`~/.codex/plugins/cache/...`). The MCP server raises an explicit error
asking for `workspace` or `AGENTMAIL_WORKSPACE` instead of silently mixing
project state into the plugin cache.

## Claude Code Channels

Claude channel delivery is a research preview path. Only enable development
channels for local plugins you trust:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

Do not use development-channel bypass flags for untrusted marketplaces.

## Codex App Server Bridge

The experimental Codex bridge connects to a Codex App Server websocket endpoint
and can start Codex turns from AgentMail messages. Prefer localhost endpoints
such as `ws://127.0.0.1:4500`.

Do not point the bridge at an endpoint you do not control. A successful bridge
delivery can make Codex process the peer message as model-visible input. The
bridge wraps each message body with per-message randomized fence strings so the
body can remain opaque while reducing delimiter-injection risk.

## Package Name

The Python distribution is `agentmail-collab`. It is unrelated to the hosted
`agentmail` PyPI package.
