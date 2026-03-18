# Overlay Mode

Use `overlay mode` only when translated output must live outside upstream source in an overlay tree or sibling repo.

## Overlay Topologies

Prefer one of these topologies:

1. `sibling incremental repo`
   Example: source repo `E:\Agent\AgentZero`, localized repo `E:\Agent\AgentZero\agent-zero_CN`
2. `in-repo user overlay`
   Example: source repo plus `usr/translation`, `usr/components`, or similar overlay paths
3. `external localized repo`
   Example: a separate repo dedicated to localized outputs

Default recommendation: `sibling incremental repo`.

## Detection Signals

Typical signals:

- upstream source is read-only or upgrade-sensitive
- runtime already prefers overlay files
- localized files must live in `usr/`, an extension layer, or a sibling repo

## Expected Inputs

- overlay adapter path
- target language
- overlay topology, usually `sibling-incremental-repo`
- export mode, usually `linked-missing`
- repo-local workflow directory

## Behavior

- Keep using the bundled overlay scripts for extraction and apply.
- Hide `import_text_bundle.py` behind the generated apply entry point.
- Generate two repo-local entry scripts even though overlay internals use three bundled scripts.
- Keep translator-facing files inside the chosen overlay topology, preferably the sibling incremental repo.

## Generated Assets

Generate these repo-local assets:

- `export_translations.cmd`
- `apply_translations.cmd`
- `export_bundle.py`
- `apply_bundle.py`
- `translation-rules.json`

The repo-local Python helpers should wrap the bundled overlay scripts and keep adapter-specific paths in config.
