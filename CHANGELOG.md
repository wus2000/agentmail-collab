# Changelog

All notable changes to AgentMail Collab are documented here.

## 0.1.0 - 2026-05-17

### Added (Stable)

- Added local peer mailbox primitives for Claude Code, Codex, and other coding
  agents.
- Added SQLite-backed rooms, agents, threads, messages, message status,
  artifacts, event timeline, and file-scope claims.
- Added stdio MCP server exposing AgentMail tools.
- Added Claude Code plugin package with MCP tools, slash commands, channel
  delivery, and a vendored Python runtime.
- Added Codex plugin package with MCP tools, skill guidance, and a vendored
  Python runtime.
- Added root marketplace entrypoints for Claude Code and Codex.
- Added `launch-codex` and `bootstrap-codex` launchers that pass
  `AGENTMAIL_DB` and `AGENTMAIL_WORKSPACE` into Codex Remote TUI sessions.
- Added `--resume` support for AgentMail-managed Codex launchers.
- Added deduplicated discovery notices when agents join a room.
- Added websocket continuation-frame support in the Codex App Server client.
- Added release-oriented documentation, bilingual onboarding docs, GitHub issue
  templates, PR template, and macOS/Linux CI matrix.

### Added (Experimental)

- Added Codex App Server bridge for Claude-to-Codex active wakeups when Codex
  runs in Remote TUI mode.
- Added bridge delivery modes:
  - `turn-start` starts a Codex turn for each delivered peer message.
  - `inject` appends model-visible context without starting a turn.

### Changed

- macOS notifications are opt-in only. `/agentmail:start` joins the room and
  configures Claude channel delivery, but it does not start an OS notification
  watcher.
- The MCP server now refuses to create a database inside a plugin cache when
  it cannot infer the project workspace. Pass `workspace` in the first tool
  call, or set `AGENTMAIL_WORKSPACE` / `CODEX_WORKSPACE_ROOT` explicitly.
- README and docs now use "AgentMail Collab" to distinguish this project from
  the hosted `agentmail` PyPI package.
- Install documentation now starts from `git clone` and explains the
  recommended global-tool, per-workspace-data setup.

### Known Limitations

- Normal Codex TUI sessions cannot be injected through the plugin/MCP layer.
  Use Remote TUI mode through `agentmail launch-codex` or
  `agentmail bootstrap-codex` for active Claude-to-Codex wakeups.
- Claude Code channels require
  `--dangerously-load-development-channels plugin:agentmail@agentmail-collab`
  while local plugin channels remain in research preview.
- macOS notifications are opt-in only; they are not part of the default wakeup
  path.
- The Claude plugin `.mcp.json` does not inject an explicit `AGENTMAIL_DB`
  default. AgentMail normally resolves the workspace database from
  `AGENTMAIL_WORKSPACE` / `${CLAUDE_PROJECT_DIR}`. Export `AGENTMAIL_DB` before
  launching both TUIs for deterministic cross-client testing.
- The root and nested local marketplace manifests currently share the
  `agentmail-collab` marketplace name. Use the repository root as the supported
  marketplace entrypoint. Adding both the root marketplace and a nested
  `plugins/*-marketplace` directory as separate marketplaces can cause a client
  name collision.
- The Python distribution is named `agentmail-collab`; it is unrelated to the
  hosted `agentmail` PyPI package.
