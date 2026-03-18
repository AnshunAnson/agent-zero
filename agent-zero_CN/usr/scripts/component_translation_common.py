from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

TRANSLATABLE_HTML_ATTRS = {"title", "aria-label", "placeholder", "alt"}
TRANSLATABLE_JS_ATTRS = {"x-text"}
VISIBLE_CHAR_RE = re.compile(r"[A-Za-z\u00C0-\u024F\u4E00-\u9FFF]")
IDENTIFIER_LIKE_RE = re.compile(r"^[a-z][a-z0-9._/-]*$")
TAG_NAME_RE = re.compile(r"<\s*([^\s>/]+)")
ATTR_RE = re.compile(
    r"""
    (?P<name>[^\s=<>'"/]+)
    (?:
        \s*=\s*
        (?:
            (?P<quote>["'])(?P<quoted>.*?)(?P=quote)
            |
            (?P<unquoted>[^\s>]+)
        )
    )?
    """,
    re.DOTALL | re.VERBOSE,
)
X_COMPONENT_RE = re.compile(
    r"<x-component\b[^>]*\bpath\s*=\s*(?P<quote>['\"])(?P<path>[^'\"]+)(?P=quote)",
    re.IGNORECASE,
)
JS_LITERAL_RE = re.compile(
    r"""
    (?P<quote>['"`])
    (?P<content>(?:\\.|(?!(?P=quote)).)*)
    (?P=quote)
    """,
    re.DOTALL | re.VERBOSE,
)
SKIP_COMPONENT_DIRS = {"_examples"}
IGNORED_TAGS = {"script", "style"}


@dataclass(slots=True)
class ExtractedEntry:
    kind: str
    tag: str
    attribute: str | None
    start: int
    end: int
    line: int
    column: int
    text: str

    def to_dict(self, file_path: str) -> dict[str, object]:
        return {
            "id": f"{file_path}:{self.kind}:{self.start}",
            "kind": self.kind,
            "tag": self.tag,
            "attribute": self.attribute,
            "start": self.start,
            "end": self.end,
            "line": self.line,
            "column": self.column,
            "text": self.text,
            "translation": "",
        }


def resolve_default_paths(script_file: str | Path) -> dict[str, Path]:
    script_path = Path(script_file).resolve()
    cn_root = script_path.parents[2]
    workspace_root = cn_root.parent
    return {
        "workspace_root": workspace_root,
        "cn_root": cn_root,
        "source_root": workspace_root / "agent-zero" / "webui" / "components",
        "target_root": cn_root / "usr" / "webui" / "components",
        "bundle_root": cn_root / "usr" / "translation",
    }


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def should_skip_component(rel_path: Path) -> bool:
    return any(part in SKIP_COMPONENT_DIRS for part in rel_path.parts)


def iter_component_files(source_root: Path, target_root: Path, mode: str) -> list[Path]:
    if mode == "linked-missing":
        return iter_linked_missing_files(source_root, target_root)

    files: list[Path] = []
    for source_path in sorted(source_root.rglob("*.html")):
        rel_path = source_path.relative_to(source_root)
        if should_skip_component(rel_path):
            continue

        target_path = target_root / rel_path
        if mode == "all":
            files.append(source_path)
        elif mode == "existing" and target_path.exists():
            files.append(source_path)
        elif mode == "missing" and not target_path.exists():
            files.append(source_path)
    return files


def iter_linked_missing_files(source_root: Path, target_root: Path) -> list[Path]:
    discovered: set[Path] = set()
    visited: set[Path] = set()
    pending: list[Path] = []

    for target_path in sorted(target_root.rglob("*.html")):
        rel_path = target_path.relative_to(target_root)
        if should_skip_component(rel_path):
            continue

        source_path = source_root / rel_path
        if source_path.exists():
            pending.append(source_path)

    while pending:
        current_path = pending.pop()
        if current_path in visited:
            continue
        visited.add(current_path)

        current_text = current_path.read_text(encoding="utf-8")
        for reference in extract_component_references(current_text):
            referenced_path = source_root / reference
            if not referenced_path.exists():
                continue

            if should_skip_component(reference):
                continue

            if referenced_path not in visited:
                pending.append(referenced_path)

            translated_path = target_root / reference
            if not translated_path.exists():
                discovered.add(referenced_path)

    return sorted(discovered)


def build_line_starts(text: str) -> list[int]:
    line_starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            line_starts.append(index + 1)
    return line_starts


def line_offset_to_index(line_starts: list[int], line: int, offset: int) -> int:
    return line_starts[line - 1] + offset


def index_to_line_column(line_starts: list[int], index: int) -> tuple[int, int]:
    line = bisect_right(line_starts, index)
    column = index - line_starts[line - 1] + 1
    return line, column


def looks_like_visible_text(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped and VISIBLE_CHAR_RE.search(stripped))


def looks_like_translatable_js_literal(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    normalized = re.sub(r"\$\{[^}]+\}", "", stripped).strip()
    if not normalized or not VISIBLE_CHAR_RE.search(normalized):
        return False

    if IDENTIFIER_LIKE_RE.fullmatch(normalized):
        return False

    return True


def extract_component_references(html_text: str) -> list[Path]:
    references: list[Path] = []
    for match in X_COMPONENT_RE.finditer(html_text):
        raw_path = match.group("path").strip()
        normalized = raw_path.lstrip("/").replace("\\", "/")
        if not normalized.endswith(".html"):
            continue
        references.append(Path(normalized))
    return references


def iter_raw_attributes(raw_tag: str) -> Iterable[tuple[str, str, int, int]]:
    tag_match = TAG_NAME_RE.match(raw_tag)
    if not tag_match:
        return []

    start_index = tag_match.end()
    results: list[tuple[str, str, int, int]] = []
    for match in ATTR_RE.finditer(raw_tag, start_index):
        name = match.group("name")
        if not name:
            continue

        quoted = match.group("quoted")
        unquoted = match.group("unquoted")
        value = quoted if quoted is not None else unquoted
        if value is None:
            continue

        if quoted is not None:
            value_start = match.start("quoted")
            value_end = match.end("quoted")
        else:
            value_start = match.start("unquoted")
            value_end = match.end("unquoted")

        results.append((name, value, value_start, value_end))
    return results


class HtmlTranslationExtractor(HTMLParser):
    def __init__(self, html_text: str) -> None:
        super().__init__(convert_charrefs=False)
        self.html_text = html_text
        self.line_starts = build_line_starts(html_text)
        self.entries: list[ExtractedEntry] = []
        self.stack: list[dict[str, object]] = []

    def extract(self) -> list[ExtractedEntry]:
        self.feed(self.html_text)
        self.close()
        return sorted(self.entries, key=lambda entry: entry.start)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._extract_attribute_entries(tag)
        self.stack.append(self._build_context(tag, attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._extract_attribute_entries(tag)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == lowered:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self._inside_ignored_context() or self._inside_icon_context():
            return

        stripped = data.strip()
        if not looks_like_visible_text(stripped):
            return

        line, offset = self.getpos()
        data_start = line_offset_to_index(self.line_starts, line, offset)
        leading = len(data) - len(data.lstrip())
        trailing = len(data) - len(data.rstrip())
        start = data_start + leading
        end = data_start + len(data) - trailing

        entry_line, entry_column = index_to_line_column(self.line_starts, start)
        current_tag = self.stack[-1]["tag"] if self.stack else "text"
        self.entries.append(
            ExtractedEntry(
                kind="text",
                tag=str(current_tag),
                attribute=None,
                start=start,
                end=end,
                line=entry_line,
                column=entry_column,
                text=self.html_text[start:end],
            )
        )

    def _build_context(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> dict[str, object]:
        classes = set()
        for name, value in attrs:
            if name == "class" and value:
                classes.update(value.split())

        return {
            "tag": tag.lower(),
            "ignored": tag.lower() in IGNORED_TAGS,
            "icon": "material-symbols-outlined" in classes,
        }

    def _inside_ignored_context(self) -> bool:
        return any(bool(frame["ignored"]) for frame in self.stack)

    def _inside_icon_context(self) -> bool:
        return any(bool(frame["icon"]) for frame in self.stack)

    def _extract_attribute_entries(self, tag: str) -> None:
        if self._inside_ignored_context():
            return

        raw_tag = self.get_starttag_text() or ""
        line, offset = self.getpos()
        tag_start = line_offset_to_index(self.line_starts, line, offset)

        for name, value, value_start, value_end in iter_raw_attributes(raw_tag):
            lowered_name = name.lower()
            absolute_start = tag_start + value_start
            absolute_end = tag_start + value_end

            if (
                lowered_name in TRANSLATABLE_HTML_ATTRS
                and looks_like_visible_text(value)
            ):
                entry_line, entry_column = index_to_line_column(
                    self.line_starts, absolute_start
                )
                self.entries.append(
                    ExtractedEntry(
                        kind="attribute",
                        tag=tag.lower(),
                        attribute=lowered_name,
                        start=absolute_start,
                        end=absolute_end,
                        line=entry_line,
                        column=entry_column,
                        text=self.html_text[absolute_start:absolute_end],
                    )
                )

            if lowered_name in TRANSLATABLE_JS_ATTRS:
                for literal in JS_LITERAL_RE.finditer(value):
                    content = literal.group("content")
                    if not looks_like_translatable_js_literal(content):
                        continue

                    literal_start = absolute_start + literal.start("content")
                    literal_end = absolute_start + literal.end("content")
                    entry_line, entry_column = index_to_line_column(
                        self.line_starts, literal_start
                    )
                    self.entries.append(
                        ExtractedEntry(
                            kind="js_literal",
                            tag=tag.lower(),
                            attribute=lowered_name,
                            start=literal_start,
                            end=literal_end,
                            line=entry_line,
                            column=entry_column,
                            text=self.html_text[literal_start:literal_end],
                        )
                    )
