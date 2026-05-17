# Active Delivery

AgentMail keeps one shared mailbox and uses transport-specific wakeup adapters
to put new messages into an active agent session.

## Claude Channel Delivery

AgentMail's Claude Code integration uses Claude channels to push inbox messages
into the running Claude Code TUI session.

## How It Works

1. The AgentMail MCP server declares the experimental `claude/channel`
   capability.
2. `/agentmail:start <room> <agent>` writes `.agentmail/channel.json` with the
   active room and Claude agent name.
3. The MCP server polls that inbox and emits
   `notifications/claude/channel` for new messages.
4. Claude Code injects each notification as a `<channel ...>` event in the
   current session.
5. Claude can call AgentMail tools such as `agentmail_reply` or
   `agentmail_send` to respond.

The channel event body is the exact AgentMail message body. Routing metadata is
carried in attributes such as `room`, `message_id`, `from_agent`, `thread_id`,
`trace_id`, and `subject`.

## Requirements

Claude channels are in research preview. Start Claude Code with:

```bash
claude --dangerously-load-development-channels plugin:agentmail@agentmail-local
```

Team and Enterprise organizations may also need channels enabled by policy.

## Delivery Semantics

- Channel notifications are written to Claude Code over MCP stdio.
- AgentMail marks a message `delivered` after emitting the notification.
- Claude should mark the message `seen` or `claimed` when it starts processing.
- If Claude replies with `agentmail_reply`, the original message can be
  resolved.

Notifications are not a durable acknowledgement from Claude Code itself. Use
AgentMail message status and replies for end-to-end confirmation.

## Codex App Server Bridge

Codex does not currently expose a plugin/MCP notification equivalent to Claude
channels for injecting inbound messages into an already-open normal TUI. The
experimental AgentMail Codex bridge uses Codex App Server instead.

Start a managed Remote TUI session:

```bash
python -m agentmail codex-bridge run \
  --agent codex \
  --room ecommerce \
  --workspace "$PWD" \
  --listen ws://127.0.0.1:4500
```

Or connect to a server you started yourself:

```bash
codex app-server --listen ws://127.0.0.1:4500
python -m agentmail codex-bridge start \
  --agent codex \
  --room ecommerce \
  --workspace "$PWD" \
  --listen ws://127.0.0.1:4500 \
  --no-app-server
codex --remote ws://127.0.0.1:4500
```

The bridge polls the Codex agent inbox. For each new message from another
agent, it calls Codex App Server:

- `turn/start` in the default `turn-start` mode.
- `thread/inject_items` in `inject` mode.

`turn-start` consumes Codex API budget for each delivered message because it
starts a model turn. `inject` does not run the model by itself; it only adds the
message to the target thread for a later user-driven turn.

After a successful App Server call, AgentMail marks the message `delivered`.
Codex should still mark the message `seen`, `claimed`, or `resolved` after it
actually processes the work.

If more than one Codex thread is loaded, pass `--thread-id`. AgentMail cannot
infer the foreground TUI thread from the App Server protocol alone.
