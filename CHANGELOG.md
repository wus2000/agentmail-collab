# Changelog

All notable changes to AgentMail are documented here.

## 0.1.0 - 2026-05-17

- Added local peer mailbox primitives for Codex and Claude Code.
- Added SQLite-backed rooms, threads, messages, artifacts, event timeline, and
  file-scope claims.
- Added stdio MCP server exposing AgentMail tools.
- Added Claude Code channel delivery for messages addressed to the configured
  Claude agent.
- Added experimental Codex App Server bridge for Claude-to-Codex active
  wakeups when Codex runs in Remote TUI mode.
- Added Claude Code and Codex plugin packages with vendored Python runtime.
- Added root marketplace entrypoints for Claude Code and Codex.
- Changed macOS notifications to opt-in only; `/agentmail:start` no longer
  starts a watcher.
