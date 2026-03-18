---
name: overlay-localization
description: Use when you need a repeatable localization workflow that exports untranslated text into a user-edited bundle and applies it back through either an overlay tree or an existing locale-file system. Best when the user should only interact with one export script and one apply script.
---

# Overlay Localization

Use this skill when you need a repeatable extract/edit/apply localization workflow with minimal user steps.

Primary goal: extract untranslated text into a compact bundle the user edits outside the chat, then apply it back with a single user-facing script.

The user-facing contract is always the same:

- one export script
- one apply script

Internal helper scripts are allowed, but the user should not need to run anything else.

## Fit Check

Use this skill when most of these are true:

- The repo has either:
  - source templates/components that need an overlay tree, or
  - existing locale files that should remain the source of truth.
- You need repeatable export/apply tooling, not one-off manual edits.
- The user should handle the actual translation text outside the model conversation.

Do not force overlay mode when built-in i18n already exists.

## Deliverable

Always leave behind exactly two user entry points:

- `export_*.cmd` or equivalent
- `apply_*.cmd` or equivalent

The expected user flow is:

1. Run export
2. Edit the text bundle
3. Run apply

## Mode Selection

Choose one mode before building anything:

- `overlay mode`
  Use when translated files must live outside upstream source in an overlay tree or sibling repo.

- `i18n mode`
  Use when the repo already has locale files such as `locales/zh-CN/*.json`, `messages.po`, or similar. In this mode, work against the existing locale files directly.

## Workflow

1. Confirm the path contract.
   Identify the source root, target overlay root or target locale file, and bundle output location.

2. Create the two user entry points.
   The scripts should be double-clickable where possible and should use absolute paths or repo-relative paths that do not depend on the current shell location.

3. Scaffold repo-specific internals.
   In overlay mode, create a repo-local adapter and use the bundled overlay scripts.
   In i18n mode, create repo-local helper scripts that export untranslated entries from locale files and apply the edited text bundle back into the target locale file.

4. Export untranslated text.
   Prefer exporting only missing or source-equal entries.
   In overlay mode, prefer `linked-missing` before `missing` or `all`.
   Emit a plain-text bundle for the user to edit.

5. Keep the text bundle human-editable.
   Preferred format: only `T` lines are user-editable.
   Do not require the user to edit JSON directly.

6. Apply from the edited text bundle directly.
   If an internal import step exists, hide it behind the apply script.
   The user should never need to run a separate import command.

7. Validate before finishing.
   Check placeholders, formatting, and whether the target file really changed.
   If runtime wiring is needed, keep it in a user-owned layer only.

## Commands

Overlay-mode internals can use the bundled scripts directly. Keep those details behind the user-facing export/apply wrappers.

If the repo already has `E:\Agent\AgentZero\.overlay-localization.json`, use it for overlay-mode internals:

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\export_bundle.py --adapter E:\Agent\AgentZero\.overlay-localization.json --text-output E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.txt
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\apply_bundle.py --adapter E:\Agent\AgentZero\.overlay-localization.json
```

For a new repo, scaffold first:

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\scaffold_adapter.py `
  --adapter E:\repo\.overlay-localization.json `
  --source-root src\templates `
  --overlay-root-template repo_{lang}\usr\templates `
  --bundle-root-template repo_{lang}\usr\translation `
  --default-lang zh-CN `
  --init-lang
```

Then export and apply:

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\export_bundle.py --adapter E:\repo\.overlay-localization.json --lang zh-CN --mode linked-missing --text-output E:\repo\repo_zh-CN\usr\translation\component-texts-linked-missing.txt
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\apply_bundle.py --adapter E:\repo\.overlay-localization.json --lang zh-CN
```

## Decision Rules

- The user-facing contract is always two scripts only: export and apply.
- Prefer the existing locale system over overlay mode when the repo already has one.
- Prefer `linked-missing` before `missing` or `all` in overlay mode.
- Keep adapters and helper scripts repo-local. The skill stays reusable; repo specifics live outside the skill.
- Default behavior is extraction and apply only. Do not generate translations in-chat unless the user explicitly asks for that.
- If an internal import step exists, hide it behind the apply script.
- Filter obvious non-translatable terms when practical: brand names, protocol names, IDs, raw URLs, and placeholder-only strings.
- Preserve placeholders and formatting exactly.
- If the repo uses HTML fragments with nested component includes, read `references/adapter-schema.md` before changing regex or path rules.
- If a runtime hook is needed, document it in the adapter comments or the task response, but keep implementation in user-owned files only.

## Resources

- `references/adapter-schema.md`: adapter fields and an example.
- `scripts/scaffold_adapter.py`: create a repo adapter and optional language skeleton.
- `scripts/export_bundle.py`: export translatable text into a JSON bundle and optional plain-text file.
- `scripts/import_text_bundle.py`: merge a human-edited plain-text file back into the JSON bundle.
- `scripts/apply_bundle.py`: apply translated text into the overlay tree.
