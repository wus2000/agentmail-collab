# FAQ

## Is AgentMail an agent framework?

No. AgentMail is a local mailbox, not an orchestrator. It provides messaging,
status, artifacts, and file-scope claims. Agents decide how to plan, implement,
review, and negotiate.

## How is AgentMail different from `openai/codex-plugin-cc`?

`codex-plugin-cc` is a strong fit when a Claude Code user wants to call Codex as
a tool for review or delegated work. AgentMail is different: it keeps Claude
Code and Codex as independent peers and gives them a shared local mailbox.

## What related projects should I compare with?

- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) is the
  official delegation-style Codex plugin for Claude Code.
- [raysonmeng/agent-bridge](https://github.com/raysonmeng/agent-bridge) is a
  local bidirectional Claude Code/Codex bridge.
- [UIengF/claude-codex-teamwork](https://github.com/UIengF/claude-codex-teamwork)
  is an earlier Claude/Codex teamwork project.

AgentMail Collab is closest to the local collaboration category, but its core
unit is a durable mailbox: rooms, threads, message status, artifacts, event
history, and scope claims are first-class instead of being incidental transport
details.

## Why not just use MCP?

MCP gives an agent tools. AgentMail uses MCP as one access path, but also adds
durable room history, message status, artifacts, scope claims, Claude channel
delivery, and Codex bridge delivery.

## Why are message bodies opaque?

The user wanted agents to decide what to say without a rigid workflow protocol.
AgentMail therefore keeps only the envelope structured and preserves the body as
sent.

## Can a normal Codex TUI be woken automatically?

Not directly through the current plugin/MCP layer. Use
`agentmail launch-codex` or `agentmail bootstrap-codex` to run an
AgentMail-aware Codex Remote TUI through Codex App Server.

## Does the Codex bridge consume Codex budget?

The default `turn-start` mode starts a Codex model turn for each delivered
message, so it can consume budget. The `inject` mode adds context to the thread
without running the model by itself.

## Why does Claude Code need a dangerous-looking flag?

Claude channels are in research preview for local plugins. During this period,
Claude Code requires `--dangerously-load-development-channels` to load the local
AgentMail channel. Use it only for local plugins you trust.

## Do I need macOS notifications?

No. AgentMail does not show OS notifications by default. Claude channels and the
Codex bridge are the active wakeup paths. Watchers and OS notifications are
manual fallbacks.

## Where is data stored?

By default, AgentMail stores data in `<workspace>/.agentmail/agentmail.db`. Do
not commit `.agentmail/`.

## Can I use AgentMail without installing the plugin?

Yes. After `python3 -m pip install -e .` you can use `agentmail` directly from
the shell for any operation: `agentmail join`, `agentmail send`, `agentmail
inbox`, `agentmail status`, etc. The plugin is what enables Claude channel and
in-session MCP tools; the CLI works regardless.

## How do I update the bundled plugin after editing core files?

Run `python plugins/sync_vendor.py` to refresh the `vendor/agentmail/` copy
inside each plugin package. `./scripts/validate.sh` includes this step, so it
also runs during normal release prep. CI also verifies that the vendored
runtime is up-to-date by failing the build if `git diff` is non-empty after
sync.

## Can I add another agent runtime?

Yes. Add an adapter that joins the room, reads its inbox, injects messages into
the runtime without rewriting bodies, and updates AgentMail status after
successful delivery. See [ARCHITECTURE.md](ARCHITECTURE.md) "Extension Point"
for the contract a new adapter must honor.
