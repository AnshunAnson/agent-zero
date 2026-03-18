# Repo Contract

The skill should leave behind repo-local assets that make the workflow usable without more chat guidance.

## Required Output

Always generate exactly two user-facing entry points:

1. `export_translations.cmd` or platform-equivalent
2. `apply_translations.cmd` or platform-equivalent

These should be double-clickable where possible and should not depend on the current shell directory.

## Recommended Layout

Keep generated assets in a repo-local workflow directory such as `localization/` or `usr/translation/`.

For `overlay mode`, prefer one of these topologies:

1. sibling incremental repo
2. in-repo user overlay
3. external localized repo

Default recommendation: `sibling incremental repo`.

Example:

- source repo: `E:\Agent\AgentZero`
- incremental repo: `E:\Agent\AgentZero\agent-zero_CN`
- workflow root: `E:\Agent\AgentZero\agent-zero_CN\usr\translation`
- localized outputs: `E:\Agent\AgentZero\agent-zero_CN\usr\...`

Recommended contents:

- `export_translations.cmd`
- `apply_translations.cmd`
- `translation-rules.json`
- `bundles/`
- `export_bundle.py`
- `apply_bundle.py`

The two Python helpers are internal assets. The translator should only use the two entry scripts and the text bundle.

## Bundle Contract

Prefer:

- one JSON bundle for machine-safe state
- one text bundle for human edits

The human-editable bundle should make it obvious that only translation lines are editable.

## Path Rules

- Prefer absolute paths inside generated entry scripts.
- Prefer repo-relative paths inside generated config when the helper scripts resolve them relative to the config file.
- Keep repo-specific values in generated config rather than hardcoding them inside the skill.
- When using a sibling incremental repo, keep all translator-facing assets and generated localized files inside that incremental repo.
