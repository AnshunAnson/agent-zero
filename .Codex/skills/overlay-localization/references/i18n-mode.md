# i18n Mode

Use `i18n mode` when the repo already has locale files and those files should remain the source of truth.

## Detection Signals

Typical signals:

- `locales/*.json`
- `messages.po`
- `*.yaml` locale files
- frontend i18n libraries such as `i18next`, `react-intl`, `vue-i18n`, or similar

If a stable locale system already exists, do not create an overlay tree just to force this skill.

## Expected Inputs

- source locale file
- target locale file
- source locale code
- target locale code
- repo-local workflow directory

## Behavior

- Export only untranslated or source-equal entries by default.
- Emit a text bundle that the translator edits outside the chat.
- Hide JSON import or merge steps behind the apply entry point.
- Keep locale files as the write target.

## Generated Assets

Generate these repo-local assets:

- `export_translations.cmd`
- `apply_translations.cmd`
- `export_bundle.py`
- `apply_bundle.py`
- `translation-rules.json`

Use the templates in `assets/i18n/` and `assets/config/`.
