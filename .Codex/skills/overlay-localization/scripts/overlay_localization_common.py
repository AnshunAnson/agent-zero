from __future__ import annotations

import hashlib
import json
import re
from bisect import bisect_right
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

DEFAULT_ADAPTER = ".overlay-localization.json"
DEFAULT_BUNDLE_NAME_TEMPLATE = "component-texts-{mode}.json"
DEFAULT_FILE_GLOB = "*.html"
DEFAULT_SOURCE_ENCODING = "utf-8"
DEFAULT_OVERLAY_ENCODING = "utf-8"
DEFAULT_TRANSLATABLE_HTML_ATTRS = {"title", "aria-label", "placeholder", "alt"}
DEFAULT_TRANSLATABLE_JS_ATTRS = {"x-text"}
DEFAULT_IGNORED_TAGS = {"script", "style"}
DEFAULT_SKIP_DIRS = {"_examples"}
DEFAULT_COMPONENT_REFERENCE_REGEX = (
    r"<x-component\b[^>]*\bpath\s*=\s*(?P<quote>['\"])(?P<path>[^'\"]+)(?P=quote)"
)
DEFAULT_COMPONENT_PATH_SUFFIX = ".html"
TEXT_BUNDLE_HEADER = "# overlay-localization-text v1"

VISIBLE_CHAR_RE = re.compile(r"[A-Za-z\u00C0-\u024F\u4E00-\u9FFF]")
IDENTIFIER_LIKE_RE = re.compile(r"^[a-z][a-z0-9._/-]*$")
TAG_NAME_RE = re.compile(r"<\s*([^\s>/]+)")
ATTR_RE = re.compile(
    r'''
    (?P<name>[^\s=<>'"/]+)
    (?:
        \s*=\s*
        (?:
            (?P<quote>["'])(?P<quoted>.*?)(?P=quote)
            |
            (?P<unquoted>[^\s>]+)
        )
    )?
    ''',
    re.DOTALL | re.VERBOSE,
)
JS_LITERAL_RE = re.compile(
    r'''
    (?P<quote>['"`])
    (?P<content>(?:\\.|(?!(?P=quote)).)*)
    (?P=quote)
    ''',
    re.DOTALL | re.VERBOSE,
)


@dataclass(slots=True)
class AdapterConfig:
    adapter_path: Path
    name: str
    lang: str
    source_root: Path
    overlay_root: Path
    bundle_root: Path
    bundle_name_template: str
    file_glob: str
    source_encoding: str
    overlay_encoding: str
    translatable_html_attrs: set[str]
    translatable_js_attrs: set[str]
    ignored_tags: set[str]
    skip_dirs: set[str]
    component_reference_regex: re.Pattern[str]
    component_path_suffix: str
    strip_leading_slash: bool
    normalize_backslashes: bool

    def bundle_path_for_mode(self, mode: str) -> Path:
        return self.bundle_root / self.bundle_name_template.format(mode=mode, lang=self.lang)


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_text_bundle(bundle: dict[str, object]) -> str:
    adapter = bundle.get("adapter", {})
    lines = [
        TEXT_BUNDLE_HEADER,
        f"# adapter={adapter.get('name', '')}",
        f"# lang={adapter.get('lang', '')}",
        f"# mode={bundle.get('mode', '')}",
        "# Edit only T lines. Keep @@ and S lines unchanged.",
        "",
    ]

    for file_info in bundle.get("files", []):
        path = str(file_info.get("path", ""))
        lines.append(f"## {path}")
        for entry in file_info.get("entries", []):
            entry_id = str(entry["id"])
            source_text = json.dumps(str(entry["text"]), ensure_ascii=False)
            translation_text = json.dumps(str(entry.get("translation", "")), ensure_ascii=False)
            lines.append(f"@@ {entry_id}")
            lines.append(f"S {source_text}")
            lines.append(f"T {translation_text}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_text_bundle(text: str) -> dict[str, str]:
    translations: dict[str, str] = {}
    current_id: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("## "):
            continue
        if line.startswith("@@ "):
            current_id = line[3:].strip()
            continue
        if line.startswith("S "):
            if current_id is None:
                raise ValueError("Found S line before any @@ entry.")
            continue
        if line.startswith("T "):
            if current_id is None:
                raise ValueError("Found T line before any @@ entry.")
            try:
                translations[current_id] = json.loads(line[2:].strip())
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON string in translation for {current_id}: {exc}") from exc
            continue
        raise ValueError(f"Unrecognized line in text bundle: {raw_line}")

    return translations


def load_adapter(adapter_path: str | Path, lang: str | None = None) -> AdapterConfig:
    adapter_file = Path(adapter_path).resolve()
    data = json.loads(adapter_file.read_text(encoding="utf-8-sig"))

    resolved_lang = lang or data.get("default_lang")
    if not resolved_lang:
        raise ValueError("No language provided. Pass --lang or set default_lang in the adapter.")

    config_dir = adapter_file.parent
    source_root = _resolve_path(config_dir, _render_template(str(data["source_root"]), resolved_lang))
    overlay_root = _resolve_path(
        config_dir,
        _render_template(str(data.get("overlay_root") or data["overlay_root_template"]), resolved_lang),
    )
    bundle_root = _resolve_path(
        config_dir,
        _render_template(str(data.get("bundle_root") or data["bundle_root_template"]), resolved_lang),
    )

    reference_pattern = re.compile(
        str(data.get("component_reference_regex", DEFAULT_COMPONENT_REFERENCE_REGEX)),
        re.IGNORECASE,
    )
    if "path" not in reference_pattern.groupindex:
        raise ValueError("component_reference_regex must define a named capture group 'path'.")

    return AdapterConfig(
        adapter_path=adapter_file,
        name=str(data.get("name", adapter_file.stem)),
        lang=str(resolved_lang),
        source_root=source_root,
        overlay_root=overlay_root,
        bundle_root=bundle_root,
        bundle_name_template=str(data.get("bundle_name_template", DEFAULT_BUNDLE_NAME_TEMPLATE)),
        file_glob=str(data.get("file_glob", DEFAULT_FILE_GLOB)),
        source_encoding=str(data.get("source_encoding", DEFAULT_SOURCE_ENCODING)),
        overlay_encoding=str(data.get("overlay_encoding", DEFAULT_OVERLAY_ENCODING)),
        translatable_html_attrs=set(_normalize_name_list(data.get("translatable_html_attrs", sorted(DEFAULT_TRANSLATABLE_HTML_ATTRS)))),
        translatable_js_attrs=set(_normalize_name_list(data.get("translatable_js_attrs", sorted(DEFAULT_TRANSLATABLE_JS_ATTRS)))),
        ignored_tags=set(_normalize_name_list(data.get("ignored_tags", sorted(DEFAULT_IGNORED_TAGS)))),
        skip_dirs=set(_normalize_name_list(data.get("skip_dirs", sorted(DEFAULT_SKIP_DIRS)))),
        component_reference_regex=reference_pattern,
        component_path_suffix=str(data.get("component_path_suffix", DEFAULT_COMPONENT_PATH_SUFFIX)),
        strip_leading_slash=bool(data.get("strip_leading_slash", True)),
        normalize_backslashes=bool(data.get("normalize_backslashes", True)),
    )


def iter_component_files(config: AdapterConfig, mode: str) -> list[Path]:
    if mode == "linked-missing":
        return iter_linked_missing_files(config)

    files: list[Path] = []
    for source_path in sorted(config.source_root.rglob(config.file_glob)):
        rel_path = source_path.relative_to(config.source_root)
        if should_skip_component(rel_path, config.skip_dirs):
            continue

        target_path = config.overlay_root / rel_path
        if mode == "all":
            files.append(source_path)
        elif mode == "existing" and target_path.exists():
            files.append(source_path)
        elif mode == "missing" and not target_path.exists():
            files.append(source_path)
    return files


def iter_linked_missing_files(config: AdapterConfig) -> list[Path]:
    discovered: set[Path] = set()
    visited: set[Path] = set()
    pending: list[Path] = []

    for overlay_path in sorted(config.overlay_root.rglob(config.file_glob)):
        rel_path = overlay_path.relative_to(config.overlay_root)
        if should_skip_component(rel_path, config.skip_dirs):
            continue

        source_path = config.source_root / rel_path
        if source_path.exists():
            pending.append(source_path)

    while pending:
        current_path = pending.pop()
        if current_path in visited:
            continue
        visited.add(current_path)

        current_text = current_path.read_text(encoding=config.source_encoding)
        for reference in extract_component_references(current_text, config):
            referenced_path = config.source_root / reference
            if not referenced_path.exists():
                continue
            if should_skip_component(reference, config.skip_dirs):
                continue
            if referenced_path not in visited:
                pending.append(referenced_path)

            overlay_path = config.overlay_root / reference
            if not overlay_path.exists():
                discovered.add(referenced_path)

    return sorted(discovered)


def should_skip_component(rel_path: Path, skip_dirs: set[str]) -> bool:
    return any(part in skip_dirs for part in rel_path.parts)


def extract_component_references(html_text: str, config: AdapterConfig) -> list[Path]:
    references: list[Path] = []
    for match in config.component_reference_regex.finditer(html_text):
        normalized = match.group("path").strip()
        if config.strip_leading_slash:
            normalized = normalized.lstrip("/")
        if config.normalize_backslashes:
            normalized = normalized.replace("\\", "/")
        if not normalized.endswith(config.component_path_suffix):
            continue
        references.append(Path(normalized))
    return references


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
    def __init__(self, html_text: str, config: AdapterConfig) -> None:
        super().__init__(convert_charrefs=False)
        self.html_text = html_text
        self.config = config
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

    def _build_context(self, tag: str, attrs: list[tuple[str, str | None]]) -> dict[str, object]:
        classes = set()
        for name, value in attrs:
            if name == "class" and value:
                classes.update(value.split())
        return {
            "tag": tag.lower(),
            "ignored": tag.lower() in self.config.ignored_tags,
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

            if lowered_name in self.config.translatable_html_attrs and looks_like_visible_text(value):
                entry_line, entry_column = index_to_line_column(self.line_starts, absolute_start)
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

            if lowered_name in self.config.translatable_js_attrs:
                for literal in JS_LITERAL_RE.finditer(value):
                    content = literal.group("content")
                    if not looks_like_translatable_js_literal(content):
                        continue

                    literal_start = absolute_start + literal.start("content")
                    literal_end = absolute_start + literal.end("content")
                    entry_line, entry_column = index_to_line_column(self.line_starts, literal_start)
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


def _normalize_name_list(values: Iterable[object]) -> list[str]:
    return [str(value).lower() for value in values]


def _render_template(template: str, lang: str) -> str:
    return template.format(lang=lang, locale=lang, language=lang)


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()
