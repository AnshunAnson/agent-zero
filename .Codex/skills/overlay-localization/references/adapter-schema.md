# Adapter Schema

Create one repo-local adapter file, usually `\.overlay-localization.json`.

This adapter only describes overlay-mode extraction and apply behavior. It does not define machine translation.

For overall mode selection and repo-local asset layout, also read:

- [overlay-mode.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/overlay-mode.md)
- [repo-contract.md](E:/Agent/AgentZero/.Codex/skills/overlay-localization/references/repo-contract.md)

The adapter defines extraction/apply behavior only. Overlay topology such as sibling incremental repo vs in-repo overlay should live in repo-local workflow config, not in the adapter itself.

User-facing workflow should still be:

1. run export script
2. edit the text bundle
3. run apply script

If an internal import step exists, keep it behind the apply script rather than exposing it to the user.

## Minimal Example

```json
{
  "name": "my-webui",
  "default_lang": "zh-CN",
  "source_root": "src/components",
  "overlay_root_template": "repo_{lang}/usr/components",
  "bundle_root_template": "repo_{lang}/usr/translation"
}
```

## Common Fields

- `name`
  Logical adapter name used in bundle metadata.

- `default_lang`
  Used when `--lang` is omitted.

- `source_root`
  Upstream template or component root.

- `overlay_root_template`
  Destination tree for generated localized files. Supports `{lang}`.

- `bundle_root_template`
  Bundle output directory. Supports `{lang}`.

- `bundle_name_template`
  Optional. Defaults to `component-texts-{mode}.json`.

- `file_glob`
  Optional. Defaults to `*.html`.

- `source_encoding`
  Optional. Defaults to `utf-8`.

- `overlay_encoding`
  Optional. Defaults to `utf-8`.

- `skip_dirs`
  Optional. Directory names to skip during export traversal. Defaults to `["_examples"]`.

- `translatable_html_attrs`
  Optional. Defaults to `["title", "aria-label", "placeholder", "alt"]`.

- `translatable_js_attrs`
  Optional. Defaults to `["x-text"]`.

- `ignored_tags`
  Optional. Defaults to `["script", "style"]`.

- `component_reference_regex`
  Optional. Regex used by `linked-missing` to discover nested components. It must expose a named capture group `path`.

- `component_path_suffix`
  Optional. Defaults to `.html`.

- `strip_leading_slash`
  Optional. Defaults to `true`.

- `normalize_backslashes`
  Optional. Defaults to `true`.

## Agent Zero Example

```json
{
  "name": "agentzero-webui-components",
  "default_lang": "CN",
  "source_root": "agent-zero/webui/components",
  "overlay_root_template": "agent-zero_{lang}/usr/webui/components",
  "bundle_root_template": "agent-zero_{lang}/usr/translation",
  "bundle_name_template": "component-texts-{mode}.json",
  "file_glob": "*.html",
  "skip_dirs": ["_examples"],
  "translatable_html_attrs": ["title", "aria-label", "placeholder", "alt"],
  "translatable_js_attrs": ["x-text"],
  "ignored_tags": ["script", "style"],
  "component_reference_regex": "<x-component\\b[^>]*\\bpath\\s*=\\s*(?P<quote>['\"])(?P<path>[^'\"]+)(?P=quote)",
  "component_path_suffix": ".html",
  "strip_leading_slash": true,
  "normalize_backslashes": true
}
```
