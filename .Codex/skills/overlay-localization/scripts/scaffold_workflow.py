from __future__ import annotations

import argparse
import json
from pathlib import Path

from overlay_localization_common import load_adapter

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS_ROOT = SKILL_ROOT / "assets"
DEFAULT_NON_TRANSLATABLE_EXACT_TERMS = ["OpenAI", "OAuth", "YouTube"]
DEFAULT_SKIP_PATTERNS = [
    r"^(?:https?://|ftp://|file://|mailto:)",
    r"^\{\{[^}]+\}\}$",
    r"^[a-z][a-z0-9._/-]*$",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scaffold repo-local translation workflow assets for i18n mode or overlay mode."
    )
    parser.add_argument("--mode", required=True, choices=["i18n", "overlay"])
    parser.add_argument("--workflow-root", required=True, help="Repo-local workflow output directory.")
    parser.add_argument("--source-locale", default="en-US")
    parser.add_argument("--target-locale", default="zh-CN")
    parser.add_argument("--source-file", default=None, help="Required for i18n mode.")
    parser.add_argument("--target-file", default=None, help="Required for i18n mode.")
    parser.add_argument("--adapter", default=None, help="Required for overlay mode.")
    parser.add_argument("--lang", default="zh-CN", help="Used for overlay mode.")
    parser.add_argument(
        "--overlay-topology",
        default="sibling-incremental-repo",
        choices=["sibling-incremental-repo", "in-repo-user-overlay", "external-localized-repo"],
        help="Used for overlay mode.",
    )
    parser.add_argument("--export-mode", default="linked-missing", help="Used for overlay mode.")
    parser.add_argument("--bundle-json", default=None)
    parser.add_argument("--bundle-text", default=None)
    return parser


def read_template(relative_path: str) -> str:
    return (ASSETS_ROOT / relative_path).read_text(encoding="utf-8")


def render_template(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2 if isinstance(value, list) else None)


def default_i18n_bundle_paths(workflow_root: Path, target_locale: str) -> tuple[Path, Path]:
    base = workflow_root / "bundles" / f"{target_locale}-untranslated"
    return base.with_suffix(".json"), base.with_suffix(".txt")


def default_overlay_bundle_paths(adapter_path: str, lang: str, export_mode: str) -> tuple[Path, Path]:
    adapter = load_adapter(adapter_path, lang)
    bundle_json = adapter.bundle_path_for_mode(export_mode)
    bundle_text = bundle_json.with_suffix(".txt")
    return bundle_json, bundle_text


def write_common_entry_points(workflow_root: Path) -> None:
    write_file(workflow_root / "export_translations.cmd", read_template("export_translations.cmd.template"))
    write_file(workflow_root / "apply_translations.cmd", read_template("apply_translations.cmd.template"))


def write_config(workflow_root: Path, config_values: dict[str, object]) -> None:
    template = read_template("config/translation-rules.json.template")
    replacements = {
        "__MODE__": json_value(config_values.get("mode")),
        "__SOURCE_LOCALE__": json_value(config_values.get("source_locale")),
        "__TARGET_LOCALE__": json_value(config_values.get("target_locale")),
        "__SOURCE_FILE__": json_value(config_values.get("source_file")),
        "__TARGET_FILE__": json_value(config_values.get("target_file")),
        "__BUNDLE_JSON__": json_value(config_values.get("bundle_json")),
        "__BUNDLE_TEXT__": json_value(config_values.get("bundle_text")),
        "__ADAPTER__": json_value(config_values.get("adapter")),
        "__LANG__": json_value(config_values.get("lang")),
        "__OVERLAY_TOPOLOGY__": json_value(config_values.get("overlay_topology")),
        "__EXPORT_MODE__": json_value(config_values.get("export_mode")),
        "__SKILL_ROOT__": json_value(config_values.get("skill_root")),
        "__NON_TRANSLATABLE_EXACT_TERMS__": json_value(config_values.get("non_translatable_exact_terms")),
        "__SKIP_PATTERNS__": json_value(config_values.get("skip_patterns")),
    }
    write_file(workflow_root / "translation-rules.json", render_template(template, replacements) + "\n")


def scaffold_i18n(args: argparse.Namespace, workflow_root: Path) -> None:
    if not args.source_file or not args.target_file:
        raise SystemExit("i18n mode requires --source-file and --target-file.")

    bundle_json, bundle_text = default_i18n_bundle_paths(workflow_root, args.target_locale)
    if args.bundle_json:
        bundle_json = Path(args.bundle_json).resolve()
    if args.bundle_text:
        bundle_text = Path(args.bundle_text).resolve()

    write_common_entry_points(workflow_root)
    write_file(workflow_root / "export_bundle.py", read_template("i18n/export_bundle.py.template"))
    write_file(workflow_root / "apply_bundle.py", read_template("i18n/apply_bundle.py.template"))
    write_config(
        workflow_root,
        {
            "mode": "i18n",
            "source_locale": args.source_locale,
            "target_locale": args.target_locale,
            "source_file": str(Path(args.source_file).resolve()),
            "target_file": str(Path(args.target_file).resolve()),
            "bundle_json": str(bundle_json),
            "bundle_text": str(bundle_text),
            "adapter": None,
            "lang": args.target_locale,
            "overlay_topology": None,
            "export_mode": None,
            "skill_root": str(SKILL_ROOT),
            "non_translatable_exact_terms": DEFAULT_NON_TRANSLATABLE_EXACT_TERMS,
            "skip_patterns": DEFAULT_SKIP_PATTERNS,
        },
    )


def scaffold_overlay(args: argparse.Namespace, workflow_root: Path) -> None:
    if not args.adapter:
        raise SystemExit("overlay mode requires --adapter.")

    bundle_json, bundle_text = default_overlay_bundle_paths(args.adapter, args.lang, args.export_mode)
    if args.bundle_json:
        bundle_json = Path(args.bundle_json).resolve()
    if args.bundle_text:
        bundle_text = Path(args.bundle_text).resolve()

    write_common_entry_points(workflow_root)
    write_file(workflow_root / "export_bundle.py", read_template("overlay/export_bundle.py.template"))
    write_file(workflow_root / "apply_bundle.py", read_template("overlay/apply_bundle.py.template"))
    write_config(
        workflow_root,
        {
            "mode": "overlay",
            "source_locale": None,
            "target_locale": args.lang,
            "source_file": None,
            "target_file": None,
            "bundle_json": str(bundle_json),
            "bundle_text": str(bundle_text),
            "adapter": str(Path(args.adapter).resolve()),
            "lang": args.lang,
            "overlay_topology": args.overlay_topology,
            "export_mode": args.export_mode,
            "skill_root": str(SKILL_ROOT),
            "non_translatable_exact_terms": DEFAULT_NON_TRANSLATABLE_EXACT_TERMS,
            "skip_patterns": DEFAULT_SKIP_PATTERNS,
        },
    )


def main() -> int:
    args = build_parser().parse_args()
    workflow_root = Path(args.workflow_root).resolve()

    if args.mode == "i18n":
        scaffold_i18n(args, workflow_root)
    else:
        scaffold_overlay(args, workflow_root)

    print(f"Workflow scaffolded: {workflow_root}")
    print(f"User entry points: {workflow_root / 'export_translations.cmd'}")
    print(f"User entry points: {workflow_root / 'apply_translations.cmd'}")
    print(f"Config written: {workflow_root / 'translation-rules.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
