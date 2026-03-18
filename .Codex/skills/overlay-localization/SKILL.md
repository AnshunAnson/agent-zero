---
name: overlay-localization
description: Use when you need a repeatable translation-repo workflow that exports untranslated text into a user-edited bundle and applies it back through either an overlay tree or an existing locale-file system. Best when the user should only interact with one export script and one apply script.
---

# Overlay Localization

Use this skill to set up a repeatable translation workflow for a repository. The workflow is always:

1. export untranslated text
2. edit the text bundle outside the chat
3. apply the edited bundle

## Trigger

Use this skill when most of these are true:

- The repo needs repeatable translation tooling, not one-off edits.
- The user should edit a compact text bundle rather than raw source files.
- The final deliverable should hide internal steps behind two user-facing entry points.
- The repo either:
  - needs a separate overlay tree for localized files, or
  - already has locale files that should remain the source of truth.

Do not force overlay mode when a stable locale system already exists.

## Output Contract

Always leave behind exactly two user entry points:

- `export_*.cmd` or platform-equivalent
- `apply_*.cmd` or platform-equivalent

The user should not need to run a third command such as `import`.

## Mode Selection

Choose one mode before generating assets:

- `i18n mode`
  Default when the repo already has locale files such as `locales/*.json`, `messages.po`, `*.yaml`, or similar.

- `overlay mode`
  Use only when translated output must live in an overlay tree or sibling repo outside upstream source.
  Default overlay topology: sibling incremental repo such as `E:\repo\repo_zh-CN`.

Read the matching reference only after choosing the mode:

- [references/i18n-mode.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/i18n-mode.md)
- [references/overlay-mode.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/overlay-mode.md)

## Workflow

1. Confirm the repo contract.
   Read [references/repo-contract.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/repo-contract.md).

2. Detect mode and required paths.
   Prefer `i18n mode` when locale files already exist.

3. Scaffold repo-local assets.
   Use `scripts/scaffold_workflow.py` to generate repo-local helpers, config, and the two user-facing entry points.

4. Export untranslated text.
   Prefer missing or source-equal entries only.

5. Keep the text bundle human-editable.
   Prefer the `T`-line format. Do not require the user to edit JSON directly.

6. Apply from the text bundle directly.
   Internal import steps are allowed, but they must stay behind the apply entry point.

7. Validate.
   Read [references/validation-rules.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/validation-rules.md).

## Commands

Use the scaffold script to generate repo-local assets.

Example for `i18n mode`:

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\scaffold_workflow.py `
  --mode i18n `
  --workflow-root E:\repo\localization `
  --source-file E:\repo\src\locales\en-US.json `
  --target-file E:\repo\src\locales\zh-CN.json `
  --source-locale en-US `
  --target-locale zh-CN
```

Example for `overlay mode`:

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\scaffold_workflow.py `
  --mode overlay `
  --workflow-root E:\repo\repo_zh-CN\usr\translation `
  --adapter E:\repo\.overlay-localization.json `
  --lang zh-CN `
  --overlay-topology sibling-incremental-repo `
  --export-mode linked-missing
```

## Decision Rules

- The user-facing contract is always two scripts only: export and apply.
- Prefer the existing locale system over overlay mode when the repo already has one.
- In overlay mode, prefer a sibling incremental repo topology before in-place overlay directories when the repo supports it.
- Prefer repo-local helpers and config over ad hoc one-off commands.
- Filter obvious non-translatable terms when practical: brand names, protocol names, IDs, raw URLs, and placeholder-only strings.
- Preserve placeholders and formatting exactly.
- Do not generate translations in-chat unless the user explicitly asks for that.
- If the repo uses HTML fragments with nested component includes, read [references/adapter-schema.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/adapter-schema.md) before changing path or regex rules.

## Resources

- [references/repo-contract.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/repo-contract.md): repo-local output contract and directory layout
- [references/i18n-mode.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/i18n-mode.md): locale-file mode rules
- [references/overlay-mode.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/overlay-mode.md): overlay-tree mode rules
- [references/validation-rules.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/validation-rules.md): filtering, placeholders, and post-apply checks
- [references/adapter-schema.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/adapter-schema.md): overlay adapter fields
- `scripts/scaffold_workflow.py`: generate repo-local assets and two user-facing entry points
- `scripts/export_bundle.py`: overlay-mode export helper
- `scripts/import_text_bundle.py`: overlay-mode text import helper used behind apply
- `scripts/apply_bundle.py`: overlay-mode apply helper
