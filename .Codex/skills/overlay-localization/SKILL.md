---
name: overlay-localization
description: Use when you need to add or maintain a language-specific overlay for a repository without modifying upstream source. Best for component or template trees where translated files should live in a separate override directory, localized sibling repo, or user-owned extension layer.
---

# Overlay Localization

Use this skill for repositories that should keep upstream source untouched while adding a specific language version through an overlay tree.

Primary goal: minimize token usage by extracting translatable text into a bundle the user edits outside the chat, then applying that bundle back into the overlay tree.

Do not use it to replace a proper built-in i18n system. If the repo already has stable locale keys and language packs, extend that system instead.

## Fit Check

Use this skill when most of these are true:

- Source templates or components live in a stable upstream tree.
- The localized version must be written to a separate directory or sibling repo.
- The runtime can be pointed at the overlay tree, or already prefers it.
- You need repeatable extract and apply tooling, not one-off manual edits.
- The user should handle the actual translation text outside the model conversation.

## Workflow

1. Confirm the overlay contract.
   Identify:
   - source root
   - overlay root or overlay root template
   - bundle output root
   - runtime entry point that should read overlay files

2. Scaffold an adapter.
   Use `scripts/scaffold_adapter.py` to create a repo-local adapter file such as `E:\repo\.overlay-localization.json`.

3. Export untranslated text.
   Use `scripts/export_bundle.py` with the adapter.
   Start with `linked-missing` for speed. It walks from already translated overlay files and discovers untranslated children, which is usually what you want for nested menus and subpanels.
   If the user wants a lower-token, human-editable format, also pass `--text-output`.

4. Fill translations.
   The user edits the bundle outside the chat.
   Preferred path: edit the plain-text file and change only `T` lines.
   JSON path: edit only each entry's `translation` field. Do not change `id`, `start`, `end`, or `path`.

5. Import the plain-text file when used.
   Use `scripts/import_text_bundle.py` to merge the edited text file back into the JSON bundle.

6. Apply the bundle.
   Use `scripts/apply_bundle.py`. It writes only into the overlay tree and refuses to apply if the upstream source changed since export.

7. Wire runtime behavior.
   If the repo does not already prefer overlay files, add the runtime hook in a user-owned layer only. Do not patch upstream source when a user override entry point exists.

## Commands

If the current repo already has `E:\Agent\AgentZero\.overlay-localization.json`, use it directly:

```powershell
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\export_bundle.py --adapter E:\Agent\AgentZero\.overlay-localization.json --text-output E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.txt
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\import_text_bundle.py --bundle E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.json --text-input E:\Agent\AgentZero\agent-zero_CN\usr\translation\component-texts-linked-missing.txt
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
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\import_text_bundle.py --bundle E:\repo\repo_zh-CN\usr\translation\component-texts-linked-missing.json --text-input E:\repo\repo_zh-CN\usr\translation\component-texts-linked-missing.txt
py -3.12 E:\Agent\AgentZero\.Codex\skills\overlay-localization\scripts\apply_bundle.py --adapter E:\repo\.overlay-localization.json --lang zh-CN
```

## Decision Rules

- Prefer `linked-missing` before `missing` or `all`.
- Keep the adapter repo-local. The skill stays reusable; the adapter captures repo specifics.
- Default behavior is extraction and apply only. Do not generate translations in-chat unless the user explicitly asks for that.
- If the repo uses HTML fragments with nested component includes, read `references/adapter-schema.md` before changing regex or path rules.
- If a runtime hook is needed, document it in the adapter comments or the task response, but keep implementation in user-owned files only.

## Resources

- `references/adapter-schema.md`: adapter fields and an example.
- `scripts/scaffold_adapter.py`: create a repo adapter and optional language skeleton.
- `scripts/export_bundle.py`: export translatable text into a JSON bundle and optional plain-text file.
- `scripts/import_text_bundle.py`: merge a human-edited plain-text file back into the JSON bundle.
- `scripts/apply_bundle.py`: apply translated text into the overlay tree.
