from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from overlay_localization_common import (
    DEFAULT_ADAPTER,
    HtmlTranslationExtractor,
    iter_component_files,
    load_adapter,
    render_text_bundle,
    sha256_text,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export translatable overlay source texts into a JSON bundle."
    )
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER, help="Repo-local adapter JSON path.")
    parser.add_argument(
        "--lang",
        default=None,
        help="Language to resolve from the adapter. Falls back to default_lang.",
    )
    parser.add_argument(
        "--mode",
        choices=("linked-missing", "missing", "existing", "all"),
        default="linked-missing",
        help="Select which source files to export.",
    )
    parser.add_argument("--bundle", default=None, help="Output bundle path override.")
    parser.add_argument(
        "--text-output",
        default=None,
        help="Optional plain-text bundle path for human translation.",
    )
    parser.add_argument("--source-root", default=None, help="Override the adapter source root for this run.")
    parser.add_argument("--target-root", default=None, help="Override the adapter overlay root for this run.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_adapter(args.adapter, args.lang)
    if args.source_root:
        config.source_root = Path(args.source_root).resolve()
    if args.target_root:
        config.overlay_root = Path(args.target_root).resolve()

    bundle_path = Path(args.bundle).resolve() if args.bundle else config.bundle_path_for_mode(args.mode)

    source_files = iter_component_files(config, args.mode)
    bundle_files: list[dict[str, object]] = []
    total_entries = 0

    for source_path in source_files:
        relative_path = source_path.relative_to(config.source_root).as_posix()
        source_text = source_path.read_text(encoding=config.source_encoding)
        entries = [
            entry.to_dict(relative_path)
            for entry in HtmlTranslationExtractor(source_text, config).extract()
        ]
        if not entries:
            continue

        total_entries += len(entries)
        bundle_files.append(
            {
                "path": relative_path,
                "source_file": str(source_path),
                "target_file": str((config.overlay_root / relative_path).resolve()),
                "sha256": sha256_text(source_text),
                "entries": entries,
            }
        )

    bundle = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "adapter": {
            "path": str(config.adapter_path),
            "name": config.name,
            "lang": config.lang,
        },
        "mode": args.mode,
        "source_root": str(config.source_root),
        "target_root": str(config.overlay_root),
        "file_count": len(bundle_files),
        "entry_count": total_entries,
        "files": bundle_files,
    }

    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    text_output_path = None
    if args.text_output:
        text_output_path = Path(args.text_output).resolve()
        text_output_path.parent.mkdir(parents=True, exist_ok=True)
        text_output_path.write_text(render_text_bundle(bundle), encoding="utf-8")

    print(f"Bundle written: {bundle_path}")
    if text_output_path:
        print(f"Text bundle written: {text_output_path}")
    print(f"Adapter: {config.name} [{config.lang}]")
    print(f"Files exported: {len(bundle_files)}")
    print(f"Entries exported: {total_entries}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
