# CLI Reference

Install the editable package first:

```bash
python3 -m pip install -e .
agentmail --help
```

Global options:

- `--db <path>`: SQLite database path. Defaults to the workspace
  `.agentmail/agentmail.db` path selected by AgentMail.
- `--json`: print JSON output.

## Room And Agent Commands

### `agentmail join`

Register or refresh an agent in a room.

```bash
agentmail join --agent codex --kind codex --room ecommerce --workspace "$PWD"
```

Important options: `--agent`, `--kind claude|codex|other`, `--room`,
`--workspace`, `--capability`, `--announce` or `--no-announce`.

### `agentmail start`

Join a room and show peers and inbox.

```bash
agentmail start --agent claude --kind claude --room ecommerce --workspace "$PWD"
```

For Claude agents, this also writes the Claude channel target config.

### `agentmail peers`

List agents in a room.

```bash
agentmail peers --room ecommerce
```

### `agentmail status`

Show DB path, room state, peers, threads, active claims, and optional inbox.

```bash
agentmail status --agent codex --room ecommerce
```

### `agentmail room-status`

Set a room to `open`, `paused`, or `closed`.

```bash
agentmail room-status --agent claude --room ecommerce --status paused
```

## Messaging Commands

### `agentmail send`

Send a free-form message.

```bash
agentmail send \
  --from codex \
  --to claude \
  --room ecommerce \
  --thread main \
  --subject "Architecture help" \
  --body "Please review the module boundaries."
```

Use `--body-file <path>` or stdin for exact multiline bodies. Use `--refs` for
a JSON refs array and `--tag` for repeated tags.

### `agentmail inbox`

List messages addressed to an agent.

```bash
agentmail inbox --agent claude --room ecommerce
```

Options include `--include-resolved`, `--unseen-only`, and `--limit`.

### `agentmail read-thread`

Read all messages in a thread.

```bash
agentmail read-thread --room ecommerce --thread main
```

### `agentmail mark`

Change message status.

```bash
agentmail mark --agent codex --message msg_xxx --status claimed
```

### `agentmail reply`

Reply to a message in the same thread.

```bash
agentmail reply --agent claude --message msg_xxx --body "I will review this."
```

Use `--resolve` to resolve the original message while replying.

### `agentmail note`

Write a shared room note addressed to all peers.

```bash
agentmail note --agent codex --room ecommerce --body "Shared context."
```

## Artifacts And Claims

### `agentmail artifact-add`

Register an artifact path.

```bash
agentmail artifact-add \
  --agent codex \
  --room ecommerce \
  --type diff \
  --path .agentmail/artifacts/orders.patch \
  --summary "Order workflow patch"
```

### `agentmail artifacts`

List artifacts for a room or thread.

```bash
agentmail artifacts --room ecommerce --thread main
```

### `agentmail claim-scope`

Claim file/path scope before editing.

```bash
agentmail claim-scope \
  --agent codex \
  --room ecommerce \
  --path src/orders \
  --reason "Implementing order workflow"
```

Options include repeated `--path`, `--ttl`, and `--force`.

### `agentmail release-scope`

Release active claims.

```bash
agentmail release-scope --agent codex --room ecommerce --path src/orders
```

### `agentmail timeline`

Show recent room events.

```bash
agentmail timeline --room ecommerce --limit 50
```

## Watchers And Claude Channels

### `agentmail watch`

Poll an inbox and print new messages.

```bash
agentmail watch --agent claude --room ecommerce --include-body
```

Use `--command` to run a callback for each new message. OS notifications are
only shown when `--notify` is set.

### `agentmail notify-start`

Start a background inbox watcher.

```bash
agentmail notify-start --agent claude --room ecommerce --workspace "$PWD"
```

OS notifications are opt-in with `--os-notify`.

### `agentmail notify-stop`

Stop a background watcher.

```bash
agentmail notify-stop --agent claude --room ecommerce --workspace "$PWD"
```

### `agentmail notify-status`

Show watcher status.

```bash
agentmail notify-status --agent claude --room ecommerce --workspace "$PWD"
```

### `agentmail channel-config`

Configure the Claude channel target room and agent.

```bash
agentmail channel-config --agent claude --room ecommerce --workspace "$PWD"
```

### `agentmail channel-status`

Show Claude channel configuration.

```bash
agentmail channel-status --workspace "$PWD"
```

## Codex Active Wakeups

### `agentmail launch-codex`

Join AgentMail and run an AgentMail-aware Codex Remote TUI.

```bash
agentmail launch-codex --room ecommerce --workspace "$PWD"
```

Options include `--listen`, `--thread-id`, `--mode turn-start|inject`,
`--resume [SESSION]`, `--keep-running`, and `--announce|--no-announce`.

### `agentmail bootstrap-codex`

Prepare the workspace and open a new AgentMail-aware Codex Remote TUI.

```bash
agentmail bootstrap-codex --room ecommerce --workspace "$PWD"
```

Use `--dry-run` to print the launch command without opening a terminal.

### `agentmail doctor`

Check local collaboration state.

```bash
agentmail doctor --room ecommerce --workspace "$PWD"
```

### `agentmail codex-bridge start`

Start the background bridge.

```bash
agentmail codex-bridge start --agent codex --room ecommerce --workspace "$PWD"
```

### `agentmail codex-bridge watch`

Run the bridge loop in the foreground.

```bash
agentmail codex-bridge watch --agent codex --room ecommerce --workspace "$PWD" --once
```

### `agentmail codex-bridge run`

Start managed App Server and bridge, then run `codex --remote` in the
foreground.

```bash
agentmail codex-bridge run --agent codex --room ecommerce --workspace "$PWD"
```

### `agentmail codex-bridge status`

Show bridge process state.

```bash
agentmail codex-bridge status --agent codex --room ecommerce --workspace "$PWD"
```

### `agentmail codex-bridge stop`

Stop bridge processes.

```bash
agentmail codex-bridge stop --agent codex --room ecommerce --workspace "$PWD"
```

## Developer Commands

### `agentmail serve`

Run the local JSON-RPC daemon.

```bash
agentmail serve --host 127.0.0.1 --port 8765
```

### `agentmail mcp`

Run the stdio MCP server.

```bash
agentmail mcp
```
