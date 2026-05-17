# Contributing

AgentMail Collab is intentionally small. Keep changes focused on the mailbox,
plugin packaging, and agent coordination primitives. The repo's value comes
from staying narrow.

## Development Loop

1. Edit the core Python package in the repository root.
2. Run the validation script:

   ```bash
   ./scripts/validate.sh
   ```

3. If you changed any file in `CORE_FILES` (see `plugins/sync_vendor.py`), the
   validation script will rerun `plugins/sync_vendor.py` so the plugin payloads
   stay self-contained. Confirm `git status` is clean before pushing — a dirty
   `plugins/*/plugins/agentmail/vendor/` tree means the bundled runtime has
   drifted from source.
4. Do not commit generated caches such as `__pycache__/`, `.agentmail/`, or
   plugin runtime logs. The `.gitignore` already excludes them.

## Before Opening a PR

A PR is ready when all of these are true:

- [ ] `./scripts/validate.sh` passes locally.
- [ ] `python plugins/sync_vendor.py` produces no `git diff`.
- [ ] `claude plugin validate .` passes (when `claude` is on PATH).
- [ ] If you added or changed an MCP tool or CLI command, update
      `docs/MCP_REFERENCE.md` or `docs/CLI_REFERENCE.md` in the same PR.
- [ ] If you changed a doc that has a Chinese sibling under `docs/zh-CN/` or
      `README.zh-CN.md`, update the Chinese version in the same PR (see
      Translation Policy below).
- [ ] CHANGELOG entry added under an appropriate `### Added` / `### Changed`
      / `### Fixed` / `### Known Limitations` subsection.

## Design Constraints

- Keep message bodies opaque and exact. Never parse, classify, rewrite,
  template, validate, or trim bodies inside the mailbox layer.
- Add only small structured envelope fields when they are broadly useful.
- Prefer natural-language coordination between agents over rigid workflows.
- Do not shell out from peer message bodies without normal user-level safety
  review. Peer messages are untrusted input.
- Keep plugin packages self-contained. Installed plugins cannot reference
  files outside their plugin cache directories, so anything new must either
  go through `vendor/agentmail/` or be added as a plugin-local asset.
- Do not ship plugin `agents/` definitions. Agent behavior is negotiated in
  message bodies, not packaged as a fixed persona.

## Translation Policy

AgentMail uses tiered translation:

- **Always translated**: `README.zh-CN.md`, `docs/zh-CN/INSTALL.md`,
  `docs/zh-CN/CONCEPTS.md`, `docs/zh-CN/README.md`.
- **English only**: reference docs (CLI, MCP), architecture, modules,
  changelog, troubleshooting, FAQ, release, security, contributing.

When you edit an English doc that has a Chinese sibling, update the Chinese
version in the same PR. When you add a brand-new doc, choose explicitly
whether it joins the translated set or stays English-only — do not silently
expand the translated set, as that doubles maintenance.

If your Chinese is not native, mark the PR with `needs-native-pass` and a
native speaker will polish before merge.

## Skills Maintenance

AgentMail has two skill surfaces that intentionally differ:

- **Top-level** (`skills/{claude,codex}/SKILL.md`): cross-project skill
  guidance referenced by parent marketplaces. Skill names are
  `agentmail-claude` / `agentmail-codex`.
- **Plugin-internal**
  (`plugins/{claude,codex}-marketplace/plugins/agentmail/skills/agentmail/SKILL.md`):
  installed-plugin skill. Skill name is `agentmail`. Body emphasizes MCP tool
  usage that is only available when the plugin is loaded.

These two are **not** synced. Each has a different audience. When you change
trigger wording or behavior, update both surfaces deliberately.

## Release Prep

Before tagging a release, read `docs/RELEASE.md` and run:

```bash
./scripts/validate.sh
```

CI mirrors the same script on macOS and Linux across Python 3.10–3.12. A
clean local run usually means a clean CI run.
