# AgentMail Collab Documentation

Pick your starting point based on what you came here to do.

## Fast Paths

- **I want to try it right now**: [INSTALL.md](INSTALL.md)
- **我看不懂英文**: [zh-CN/README.md](zh-CN/README.md)
- **It broke**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Is this the right tool for me?**: [FAQ.md](FAQ.md)
- **I'm preparing a release**: [RELEASE.md](RELEASE.md)
- **I'm about to read/write code**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Security review**: [../SECURITY.md](../SECURITY.md)

## Learn The Model

- [CONCEPTS.md](CONCEPTS.md): workspace, rooms, threads, messages, status,
  inbox, claims, artifacts, timeline, channels, and bridges.
- [ARCHITECTURE.md](ARCHITECTURE.md): one local mailbox with transport
  adapters for Claude Code and Codex, the global-tool / per-workspace-data
  deployment posture, and the Python module map.
- [FAQ.md](FAQ.md): positioning and common questions.

## Install And Operate

- [INSTALL.md](INSTALL.md): from-source install, global/user-scope setup,
  per-workspace data model, and smoke test.
- [CHANNELS.md](CHANNELS.md): Claude Code channel delivery.
- [CODEX_BRIDGE.md](CODEX_BRIDGE.md): Codex App Server bridge and Remote TUI
  wakeups.
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md): common local failures and recovery.

## Reference

- [CLI_REFERENCE.md](CLI_REFERENCE.md): `agentmail` command inventory.
- [MCP_REFERENCE.md](MCP_REFERENCE.md): MCP tool inventory for Claude Code and
  Codex plugin sessions.
- [TESTING.md](TESTING.md): automated and live collaboration tests.
- [RELEASE.md](RELEASE.md): release checklist.

## Documentation Policy

English docs are the source of truth for technical reference. Chinese docs cover
the first-run onboarding path: `README`, `INSTALL`, and `CONCEPTS`. When those
English source docs change, update the matching Chinese docs before release.
