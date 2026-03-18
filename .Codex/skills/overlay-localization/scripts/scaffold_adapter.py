from __future__ import annotations

import argparse
import json
from pathlib import Path

from overlay_localization_common import DEFAULT_ADAPTER


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a repo-local adapter for overlay localization."
    )
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER, help="Adapter JSON path to create.")
    parser.add_argument("--name", default=None, help="Logical adapter name.")
    parser.add_argument("--source-root", required=True, help="Upstream source root.")
    parser.add_argument(
        "--overlay-root-template",
        required=True,
        help="Overlay root path template. Supports {lang}.",
    )
    parser.add_argument(
        "--bundle-root-template",
        required=True,
        help="Bundle root path template. Supports {lang}.",
    )
    parser.add_argument(
        "--default-lang",
        default="zh-CN",
        help="Default language used when --lang is omitted later.",
    )
    parser.add_argument(
        "--bundle-name-template",
        default="component-texts-{mode}.json",
        help="Bundle filename template. Supports {mode} and {lang}.",
    )
    parser.add_argument("--file-glob", default="*.html", help="File glob to scan.")
    parser.add_argument(
        "--init-lang",
        action="store_true",
        help="Create overlay and bundle directories for the default language.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing adapter file.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    adapter_path = Path(args.adapter).resolve()

    if adapter_path.exists() and not args.force:
        raise SystemExit(f"Adapter already exists: {adapter_path}")

    name = args.name or adapter_path.stem.lstrip(".") or "overlay-localization"
    adapter = {
        "name": name,
        "default_lang": args.default_lang,
        "source_root": args.source_root,
        "overlay_root_template": args.overlay_root_template,
        "bundle_root_template": args.bundle_root_template,
        "bundle_name_template": args.bundle_name_template,
        "file_glob": args.file_glob,
        "source_encoding": "utf-8",
        "overlay_encoding": "utf-8",
        "skip_dirs": ["_examples"],
        "translatable_html_attrs": ["title", "aria-label", "placeholder", "alt"],
        "translatable_js_attrs": ["x-text"],
        "ignored_tags": ["script", "style"],
        "component_reference_regex": (
            "<x-component\\\\b[^>]*\\\\bpath\\\\s*=\\\\s*(?P<quote>['\\\"])(?P<path>[^'\\\"]+)(?P=quote)"
        ),
        "component_path_suffix": ".html",
        "strip_leading_slash": True,
        "normalize_backslashes": True,
    }

    adapter_path.parent.mkdir(parents=True, exist_ok=True)
    adapter_path.write_text(json.dumps(adapter, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.init_lang:
        overlay_root = Path(args.overlay_root_template.format(lang=args.default_lang))
        bundle_root = Path(args.bundle_root_template.format(lang=args.default_lang))
        if not overlay_root.is_absolute():
            overlay_root = (adapter_path.parent / overlay_root).resolve()
        if not bundle_root.is_absolute():
            bundle_root = (adapter_path.parent / bundle_root).resolve()
        overlay_root.mkdir(parents=True, exist_ok=True)
        bundle_root.mkdir(parents=True, exist_ok=True)
        print(f"Overlay root ready: {overlay_root}")
        print(f"Bundle root ready: {bundle_root}")

    print(f"Adapter written: {adapter_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
