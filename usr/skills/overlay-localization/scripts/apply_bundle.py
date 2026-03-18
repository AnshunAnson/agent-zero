from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from overlay_localization_common import DEFAULT_ADAPTER, load_adapter, sha256_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply translated overlay texts from a JSON bundle."
    )
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER, help="Repo-local adapter JSON path.")
    parser.add_argument(
        "--lang",
        default=None,
        help="Language to resolve from the adapter. Falls back to default_lang.",
    )
    parser.add_argument(
        "--bundle",
        default=None,
        help="JSON bundle path. Defaults to the linked-missing bundle for the resolved language.",
    )
    parser.add_argument(
        "--mode",
        choices=("linked-missing", "missing", "existing", "all"),
        default="linked-missing",
        help="Used only when --bundle is omitted.",
    )
    parser.add_argument("--source-root", default=None, help="Override the adapter source root for this run.")
    parser.add_argument("--target-root", default=None, help="Override the adapter overlay root for this run.")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Overwrite existing overlay files without creating a backup copy.",
    )
    return parser


def backup_if_needed(target_path: Path) -> Path | None:
    if not target_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = target_path.with_suffix(f"{target_path.suffix}.bak-{timestamp}")
    shutil.copy2(target_path, backup_path)
    return backup_path


def main() -> int:
    args = build_parser().parse_args()
    config = load_adapter(args.adapter, args.lang)
    if args.source_root:
        config.source_root = Path(args.source_root).resolve()
    if args.target_root:
        config.overlay_root = Path(args.target_root).resolve()

    bundle_path = Path(args.bundle).resolve() if args.bundle else config.bundle_path_for_mode(args.mode)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
    written_files = 0
    changed_entries = 0
    backups: list[Path] = []

    for file_info in bundle.get("files", []):
        relative_path = Path(file_info["path"])
        source_path = config.source_root / relative_path
        target_path = config.overlay_root / relative_path
        source_text = source_path.read_text(encoding=config.source_encoding)
        source_hash = sha256_text(source_text)

        if source_hash != file_info["sha256"]:
            raise RuntimeError(
                f"Source file changed since export: {source_path}. Regenerate the bundle first."
            )

        replacements = [
            entry
            for entry in file_info["entries"]
            if entry.get("translation") not in ("", None)
            and entry["translation"] != entry["text"]
        ]
        if not replacements:
            continue

        updated_text = source_text
        for entry in sorted(replacements, key=lambda item: item["start"], reverse=True):
            start = int(entry["start"])
            end = int(entry["end"])
            original_text = str(entry["text"])
            current_text = updated_text[start:end]
            if current_text != original_text:
                raise RuntimeError(
                    f"Span mismatch in {source_path} at {entry['line']}:{entry['column']} "
                    f"for entry {entry['id']}."
                )

            updated_text = updated_text[:start] + str(entry["translation"]) + updated_text[end:]

        target_path.parent.mkdir(parents=True, exist_ok=True)
        previous_text = target_path.read_text(encoding=config.overlay_encoding) if target_path.exists() else None
        if previous_text == updated_text:
            continue

        if target_path.exists() and not args.no_backup:
            backup_path = backup_if_needed(target_path)
            if backup_path:
                backups.append(backup_path)

        target_path.write_text(updated_text, encoding=config.overlay_encoding)
        written_files += 1
        changed_entries += len(replacements)

    print(f"Bundle applied: {bundle_path}")
    print(f"Adapter: {config.name} [{config.lang}]")
    print(f"Files written: {written_files}")
    print(f"Entries replaced: {changed_entries}")
    if backups:
        print(f"Backups created: {len(backups)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
