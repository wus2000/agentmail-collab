# Codex Bridge

The Codex bridge delivers AgentMail inbox messages into Codex through Codex App
Server and Remote TUI mode.

The bridge is experimental in this release. It depends on Codex App Server and
Remote TUI APIs that may change in future Codex versions.

## Why It Exists

Claude Code exposes channels that can inject AgentMail messages into a running
Claude Code session. Normal Codex plugin and MCP sessions do not currently
provide the same injection path for an already-open TUI. AgentMail therefore
uses Codex App Server as the active Claude-to-Codex wakeup adapter.

## Recommended Launcher

From the project directory:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

Resume the most recent Codex session:

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

`launch-codex` starts:

- `codex app-server`
- an AgentMail bridge loop
- `codex --remote <listen-url>`

It forwards `AGENTMAIL_DB` and `AGENTMAIL_WORKSPACE` into the spawned Codex
process so the MCP tools and bridge use the same database.

## Bootstrap From A Normal Codex TUI

If you already opened a normal Codex TUI, ask it to run:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

To resume the latest session in the new Remote TUI:

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD" --resume last
```

The original normal TUI remains normal. Continue active-wakeup collaboration in
the new Remote TUI.

## Delivery Modes

`turn-start` is the default:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --mode turn-start
```

It calls Codex App Server `turn/start`, which starts a Codex model turn. This
uses Codex API budget for each delivered peer message.

`inject` appends context without starting a model turn:

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD" --mode inject
```

It calls `thread/inject_items`. Use it when you want the message visible in
the thread but do not want Codex to run until the user submits a later turn.

## Manual Pieces

You can run the components yourself:

```bash
codex app-server --listen ws://127.0.0.1:4500
agentmail codex-bridge start \
  --agent codex \
  --room ecommerce \
  --workspace "$PWD" \
  --listen ws://127.0.0.1:4500 \
  --no-app-server
codex --remote ws://127.0.0.1:4500
```

Foreground bridge loop for debugging:

```bash
agentmail codex-bridge watch \
  --agent codex \
  --room ecommerce \
  --workspace "$PWD" \
  --listen ws://127.0.0.1:4500 \
  --once
```

## Thread Selection

If exactly one Codex thread is loaded, AgentMail can target it. If multiple
threads are loaded, pass `--thread-id`:

```bash
agentmail launch-codex \
  --room ecommerce \
  --workspace "$PWD" \
  --thread-id <codex-thread-id>
```

AgentMail cannot infer the foreground TUI thread from the App Server protocol
alone.

## Status And Logs

```bash
agentmail codex-bridge status --agent codex --room ecommerce --workspace "$PWD"
```

Bridge state is stored under:

```text
<workspace>/.agentmail/codex-bridge/
<workspace>/.agentmail/logs/
```

Stop managed bridge processes:

```bash
agentmail codex-bridge stop --agent codex --room ecommerce --workspace "$PWD"
```

## Delivery Semantics

- The bridge polls the Codex agent inbox.
- It skips self-origin messages.
- It preserves the AgentMail body inside per-message random fence strings.
- It marks a message `delivered` only after the Codex App Server call succeeds.
- If delivery fails, the running bridge retries on a later poll.
- Codex should still mark the message `seen`, `claimed`, or `resolved` after it
  acts on the work.

## Security Notes

Prefer localhost App Server endpoints such as `ws://127.0.0.1:4500`. Do not
point the bridge at an endpoint you do not control. A successful bridge delivery
can make Codex process a peer message as model-visible input.

The bridge supports websocket continuation frames and validates local readiness
for managed `codex app-server` processes.
