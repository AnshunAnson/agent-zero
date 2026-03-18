from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from component_translation_common import (
    HtmlTranslationExtractor,
    iter_component_files,
    resolve_default_paths,
    sha256_text,
)


def build_parser() -> argparse.ArgumentParser:
    defaults = resolve_default_paths(__file__)
    parser = argparse.ArgumentParser(
        description="Export translatable component texts into a JSON bundle."
    )
    parser.add_argument(
        "--mode",
        choices=("linked-missing", "missing", "existing", "all"),
        default="linked-missing",
        help="Select which upstream components to export.",
    )
    parser.add_argument(
        "--source-root",
        default=str(defaults["source_root"]),
        help="Upstream component root to scan.",
    )
    parser.add_argument(
        "--target-root",
        default=str(defaults["target_root"]),
        help="Translated component root used to resolve missing/existing files.",
    )
    parser.add_argument(
        "--bundle",
        default=None,
        help="Output JSON bundle path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    defaults = resolve_default_paths(__file__)
    source_root = Path(args.source_root).resolve()
    target_root = Path(args.target_root).resolve()
    bundle_path = (
        Path(args.bundle).resolve()
        if args.bundle
        else (defaults["bundle_root"] / f"component-texts-{args.mode}.json").resolve()
    )

    source_files = iter_component_files(source_root, target_root, args.mode)
    bundle_files: list[dict[str, object]] = []
    total_entries = 0

    for source_path in source_files:
        relative_path = source_path.relative_to(source_root).as_posix()
        source_text = source_path.read_text(encoding="utf-8")
        entries = [
            entry.to_dict(relative_path)
            for entry in HtmlTranslationExtractor(source_text).extract()
        ]
        if not entries:
            continue

        total_entries += len(entries)
        bundle_files.append(
            {
                "path": relative_path,
                "source_file": str(source_path),
                "target_file": str((target_root / relative_path).resolve()),
                "sha256": sha256_text(source_text),
                "entries": entries,
            }
        )

    bundle = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "source_root": str(source_root),
        "target_root": str(target_root),
        "file_count": len(bundle_files),
        "entry_count": total_entries,
        "files": bundle_files,
    }

    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Bundle written: {bundle_path}")
    print(f"Files exported: {len(bundle_files)}")
    print(f"Entries exported: {total_entries}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
