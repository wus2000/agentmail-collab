# Install AgentMail Collab

This guide starts from a fresh source checkout and installs AgentMail for
day-to-day use with Claude Code and Codex.

## Quick Reference

AgentMail has two different kinds of state:

- **Tools can be installed once**: the `agentmail` CLI, Claude Code plugin, and
  Codex plugin can live in user/global plugin locations.
- **Collaboration data stays per project**: each project should use its own
  `<project>/.agentmail/agentmail.db`, bridge state, and logs.

Do not globally export `AGENTMAIL_DB=$HOME/.agentmail/agentmail.db` in shell
startup files. That makes unrelated projects share one room namespace and one
message history. Use `AGENTMAIL_DB` only per shell/project when you need an
explicit database path.

## Prerequisites

- Git.
- Python 3.10 or newer available as `python3`.
- Claude Code installed and authenticated.
- Codex installed and authenticated.
- macOS or Linux for the best-tested local workflow. Windows users should use
  WSL for now.

## Get The Source

Clone the repository and enter the AgentMail repo root:

```bash
git clone https://github.com/wus2000/agentmail-collab agentmail-collab
cd agentmail-collab
```

Before installing, you can run the full local validation suite:

```bash
./scripts/validate.sh
```

That script checks Python tests, JSON manifests, vendored plugin runtime drift,
and plugin packaging assumptions.

## Install The CLI

Install the `agentmail` command from this checkout:

```bash
python3 -m pip install -e .
agentmail --help
```

This installs into your active Python environment. If you normally install
developer tools with `--user`, `pipx`, `uv tool`, or a project venv, use the
equivalent workflow for your machine. The important outcome is that
`agentmail` resolves on your `PATH`.

After a package-index release, the non-editable form will be:

```bash
python3 -m pip install agentmail-collab
```

Until then, use the editable source checkout.

## Install The Claude Code Plugin

Validate the repository root as a Claude Code marketplace:

```bash
claude plugin validate .
```

For long-term use across projects, add and install the marketplace at user
scope:

```bash
claude plugin marketplace add "$(pwd)" --scope user
claude plugin install agentmail@agentmail-collab --scope user
```

Claude Code supports `user`, `project`, and `local` plugin scopes. Use `user`
for normal global installs, `project` when a repository should declare the
plugin for that project, and `local` when you are actively developing or
testing this checkout. For a local install:

```bash
claude plugin marketplace add "$(pwd)" --scope local
claude plugin install agentmail@agentmail-collab --scope local
```

If you already have Claude Code open, reload plugins:

```text
/reload-plugins
```

Claude Code channel delivery for local plugins is currently a research-preview
path. Start Claude Code with the channel flag when you want inbound AgentMail
messages to appear in the running Claude session:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

## Install The Codex Plugin

Add the same repository root as a Codex plugin marketplace:

```bash
codex plugin marketplace add "$(pwd)"
```

Restart Codex, open `/plugins`, choose `AgentMail Collab`, and install
`agentmail`.

Codex's marketplace command accepts local marketplace roots, Git URLs, and
`owner/repo[@ref]` sources. For a personal/global setup, point Codex at a
stable checkout path or published Git repository and reinstall/update the
plugin from `/plugins` after you pull changes.

## Use AgentMail In A Project

Move to the real codebase where you want Claude Code and Codex to collaborate:

```bash
cd /path/to/your-project
```

The first agent to join a room creates it. Claude Code does not need to be
first; Codex can create the room first, or both can join an existing room.
Examples in this guide use room `ecommerce`, Claude agent name `claude`, and
Codex agent name `codex`, but those names are not special.

Start Claude Code with channel support from the project directory:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-collab
```

Then join the room inside Claude Code:

```text
/agentmail:start ecommerce claude
```

The slash command shape is:

```text
/agentmail:start <room> <agent>
```

For explicit mailbox access from a normal Codex TUI, ask Codex:

```text
Use @agentmail. Join room ecommerce as codex, list peers, and check my inbox.
```

For CLI-only setup, either side can join directly:

```bash
agentmail join --room ecommerce --agent codex --kind codex --workspace "$PWD" --announce
agentmail join --room ecommerce --agent claude --kind claude --workspace "$PWD" --announce
```

CLI commands that accept `--workspace` default it to `.`, so run them from the
project root or pass `--workspace /path/to/your-project` explicitly. Commands
that do not expose `--workspace` use the current directory, `--db`, or
`AGENTMAIL_DB` to find the project database.

## Active Wakeups Per Project

Claude Code can receive AgentMail messages through Claude channels after the
channel flag is enabled. Codex does not currently expose the same injection
surface for an already-open normal TUI, so AgentMail uses Codex App Server and
Remote TUI mode for active Claude-to-Codex wakeups.

The recommended Codex active-wakeup launcher is:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

Resume the most recent Codex session through the same wakeup path:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --resume last
```

Resume a specific session:

```bash
agentmail launch-codex \
  --room ecommerce \
  --workspace "$PWD" \
  --resume 019e3459-262e-7f53-b30d-a6c199f67606
```

The launcher joins the room, sets `AGENTMAIL_DB` and `AGENTMAIL_WORKSPACE` for
the spawned Codex process, starts `codex app-server`, starts an AgentMail bridge
loop, and opens `codex --remote ...`.

Startup commands send one deduplicated discovery notice to already-online
peers so the other TUI can see that a peer joined. Use `--no-announce` for a
quiet startup.

If you already opened a normal Codex TUI, ask it to run:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

To bootstrap into the most recent Codex session:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD" --resume last
```

`bootstrap-codex` opens a new AgentMail-aware Codex Remote TUI. Continue the
active-wakeup collaboration in that new window; the original normal Codex TUI
cannot be injected directly through the plugin/MCP layer.

Check the project setup:

```bash
agentmail doctor --room ecommerce --workspace "$PWD"
```

## Where Data Lives

| Path | Role | Scope |
| --- | --- | --- |
| Python environment containing `agentmail` | CLI and `agentmail-mcp` entrypoints | User/tool install |
| Claude Code plugin cache or user plugin install | Claude plugin payload and vendored runtime | User/tool install |
| Codex plugin install/cache | Codex plugin payload and vendored runtime | User/tool install |
| `<project>/.agentmail/agentmail.db` | Rooms, agents, threads, messages, status, artifacts, claims, timeline | Project data |
| `<project>/.agentmail/channel.json` | Claude channel delivery state | Project data |
| `<project>/.agentmail/codex-bridge/` | Codex bridge pid/status files | Project data |
| `<project>/.agentmail/logs/` | Local AgentMail logs | Project data |

Commit the tool source and plugin package if you are maintaining AgentMail, but
do not commit project `.agentmail/` runtime state.

## Explicit Database Paths

AgentMail normally resolves the project database from:

1. `--db`, when a CLI command provides it.
2. `AGENTMAIL_DB`, when set.
3. An explicit `workspace` argument from a CLI/MCP call.
4. `AGENTMAIL_WORKSPACE`, `CLAUDE_PROJECT_DIR`, or `CODEX_WORKSPACE_ROOT`.
5. The current working directory.

For deterministic local testing, set an explicit database only in the shell for
one project:

```bash
cd /path/to/your-project
export AGENTMAIL_DB="$PWD/.agentmail/agentmail.db"
```

Do not put that export in `~/.zshrc`, `~/.bashrc`, or another global startup
file unless you intentionally want every project to share one mailbox.

## Plugin Cache Protection

Global plugin installs may run MCP servers from a plugin cache directory. That
cache is tool state, not a project workspace. Starting in v0.1.0, AgentMail
refuses to create a database inside a plugin cache when it cannot infer the
real project workspace.

If you see an error like:

```text
AgentMail cannot infer the project workspace.
```

fix the first join call by passing `workspace`, or launch the client with a
project-specific environment:

```bash
export AGENTMAIL_WORKSPACE="$PWD"
```

The managed launcher already does this for Codex:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for cleanup steps if an older
build created a database under a plugin cache.

## Smoke Test

From Codex, ask Claude to acknowledge a channel message:

```text
Use @agentmail. Send Claude a message in room ecommerce asking it to reply with AGENTMAIL_SMOKE_ACK.
```

Expected result:

- Claude receives the message in the running Claude Code session.
- Claude replies through `agentmail_reply`.
- Codex can read the reply in its AgentMail inbox.
- If Codex was started through `launch-codex` or `bootstrap-codex`,
  Claude-origin messages can also start a Codex turn through Codex App Server.

You can inspect the room from a shell:

```bash
agentmail status --room ecommerce
agentmail inbox --agent codex --room ecommerce
agentmail timeline --room ecommerce
```

## Update An Existing Install

For a source install:

```bash
cd /path/to/agentmail-collab
git pull
python3 -m pip install -e .
python plugins/sync_vendor.py --check
./scripts/validate.sh
```

If the plugin payload changed, reinstall or update the client plugin from the
same marketplace source:

```bash
claude plugin install agentmail@agentmail-collab --scope user
codex plugin marketplace add "$(pwd)"
```

Then reload/restart the relevant TUI:

```text
/reload-plugins
```

For Codex, restart Codex and use `/plugins` to update or reinstall
`AgentMail Collab` if the UI still shows an older plugin payload.

## Notes

- AgentMail does not show macOS notifications by default.
- Claude Code channels are a research-preview feature and require
  `--dangerously-load-development-channels` for this local plugin.
- Normal Codex TUI sessions cannot be injected directly through plugin/MCP.
  Use `launch-codex` or `bootstrap-codex` for active wakeups.
- Message bodies are free-form and preserved as sent; only envelope fields are
  structured.
