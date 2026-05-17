# Contributing

AgentMail is intentionally small. Keep changes focused on the mailbox,
plugin packaging, and agent coordination primitives.

## Development Loop

1. Edit the core Python package in the repository root.
2. Run the tests:

   ```bash
   ./scripts/validate.sh
   ```

3. If core Python files changed, `scripts/validate.sh` runs
   `plugins/sync_vendor.py` so the Claude Code and Codex plugin packages stay
   self-contained.
4. Do not commit generated caches such as `__pycache__`, `.agentmail`, or
   plugin runtime logs.

## Design Constraints

- Keep message bodies opaque and exact.
- Add only small structured envelope fields when they are broadly useful.
- Prefer natural-language coordination between agents over rigid workflows.
- Avoid shelling out from peer message bodies without normal user-level safety
  review.
- Keep plugin packages self-contained; installed plugins cannot reference files
  outside their plugin cache directories.

## Release Prep

Before release, read `docs/RELEASE.md` and run:

```bash
./scripts/validate.sh
```
