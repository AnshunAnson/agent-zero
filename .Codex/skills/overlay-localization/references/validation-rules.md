# Validation Rules

Apply these checks by default unless the user explicitly opts out.

## Export-Side Filtering

Prefer filtering out obvious non-translation entries when practical:

- known brand or product names
- protocol names
- raw URLs
- placeholder-only strings
- token-like or identifier-like strings

Keep this rule configurable through repo-local config rather than hardcoding everything in the skill.

## Apply-Side Validation

Before writing translated output:

- reject placeholder mismatches such as missing `{{name}}`
- reject invalid JSON string content when the bundle format requires JSON strings
- skip blank translations instead of overwriting with empty values

## Post-Apply Checks

After apply:

- verify the target file really changed when changes were expected
- verify the bundle state and target file are in sync
- surface a short summary of updated, skipped, and rejected entries
