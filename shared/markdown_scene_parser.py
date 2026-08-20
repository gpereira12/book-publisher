"""Parser determinístico de manuscritos Markdown para o índice editorial.

O parser não altera o manuscrito. IDs explícitos são lidos de comentários como
``<!-- chapter:... -->`` e ``<!-- scene:... -->``. Quando não existem, o Harness
resolve identidades usando o banco anterior e, por último, UUID5 determinístico.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final


PARSER_VERSION: Final = "1.0.0"

_ATX_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_HTML_HEADING = re.compile(
    r"^[ \t]*<h([1-6])\b[^>]*>(.*?)</h\1>[ \t]*$", re.IGNORECASE
)
_MARKER = re.compile(
    r"^[ \t]*<!--[ \t]*(chapter|scene)[ \t]*:[ \t]*"
    r"(?:id[ \t]*=[ \t]*)?([A-Za-z0-9._:-]+)"
    r"(?:[ \t]+title[ \t]*=[ \t]*\"([^\"]*)\")?[ \t]*-->[ \t]*$",
    re.IGNORECASE,
)
_HORIZONTAL_RULE = re.compile(r"^[ \t]*(?:\*[ \t]*){3,}$|^[ \t]*(?:-[ \t]*){3,}$|^[ \t]*(?:_[ \t]*){3,}$")
_SEMANTIC_CHAPTER = re.compile(
    r"^(?:cap[ií]tulo|chapter|dia)[ \t]+(?:\d+|[ivxlcdm]+)\b", re.IGNORECASE
)
_NUMBERED_HEADING = re.compile(r"^\d+[.)][ \t]+")
_STRUCTURAL_HEADING = re.compile(
    r"^(?:parte\b|part\b|apresenta[cç][aã]o\b|introdu[cç][aã]o\b|"
    r"conclus[aã]o\b|pref[aá]cio\b|refer[eê]ncias\b)",
    re.IGNORECASE,
)
_WORD = re.compile(r"[\wÀ-ÖØ-öø-ÿ]+", re.UNICODE)


class MarkdownParseError(ValueError):
    """O manuscrito não pode ser segmentado de forma segura."""


@dataclass(frozen=True, slots=True)
class PassageDraft:
    ordinal: int
    start_offset: int
    end_offset: int
    start_line: int
    end_line: int
    content: str
    content_sha256: str
    token_count: int


@dataclass(frozen=True, slots=True)
class SceneDraft:
    ordinal: int
    stable_key: str
    declared_uid: str | None
    title: str | None
    start_line: int
    end_line: int
    content: str
    content_sha256: str
    token_count: int
    passages: tuple[PassageDraft, ...]


@dataclass(frozen=True, slots=True)
class ChapterDraft:
    ordinal: int
    stable_key: str
    declared_uid: str | None
    title: str | None
    start_line: int
    end_line: int
    scenes: tuple[SceneDraft, ...]


@dataclass(frozen=True, slots=True)
class ParsedManuscript:
    source_path: Path
    content_sha256: str
    byte_size: int
    chapters: tuple[ChapterDraft, ...]
    parser_version: str = PARSER_VERSION


@dataclass(frozen=True, slots=True)
class _Heading:
    line_index: int
    level: int
    title: str


@dataclass(frozen=True, slots=True)
class _Marker:
    line_index: int
    kind: str
    uid: str
    title: str | None


@dataclass(frozen=True, slots=True)
class _Boundary:
    line_index: int
    content_start: int
    title: str | None
    declared_uid: str | None


def _clean_title(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.replace("\\.", ".")
    value = re.sub(r"^[*_`~]+|[*_`~]+$", "", value.strip())
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def slugify(value: str, *, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or fallback


def _frontmatter_end(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            return index + 1
    raise MarkdownParseError("frontmatter YAML iniciado, mas não encerrado")


def _scan_structure(lines: list[str]) -> tuple[list[_Heading], list[_Marker]]:
    headings: list[_Heading] = []
    markers: list[_Marker] = []
    fenced = False
    fence_char: str | None = None
    for index, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        fence = re.match(r"^[ \t]*(`{3,}|~{3,})", stripped)
        if fence:
            char = fence.group(1)[0]
            if not fenced:
                fenced, fence_char = True, char
            elif char == fence_char:
                fenced, fence_char = False, None
            continue
        if fenced:
            continue

        marker_match = _MARKER.match(stripped)
        if marker_match:
            markers.append(
                _Marker(
                    line_index=index,
                    kind=marker_match.group(1).lower(),
                    uid=marker_match.group(2),
                    title=_clean_title(marker_match.group(3)) if marker_match.group(3) else None,
                )
            )
            continue
        atx = _ATX_HEADING.match(stripped)
        if atx:
            headings.append(
                _Heading(index, len(atx.group(1)), _clean_title(atx.group(2)))
            )
            continue
        html_heading = _HTML_HEADING.match(stripped)
        if html_heading:
            headings.append(
                _Heading(
                    index,
                    int(html_heading.group(1)),
                    _clean_title(html_heading.group(2)),
                )
            )
    return headings, markers


def _has_meaningful_content(lines: list[str], start: int, end: int) -> bool:
    for line in lines[start:end]:
        stripped = line.strip()
        if stripped and not _HORIZONTAL_RULE.match(stripped):
            return True
    return False


def _has_scene_content(lines: list[str], start: int, end: int) -> bool:
    """Distingue prosa de um cabeçalho estrutural antes do primeiro marcador."""

    for line in lines[start:end]:
        stripped = line.strip()
        if not stripped or _HORIZONTAL_RULE.match(stripped):
            continue
        if _ATX_HEADING.match(stripped) or _HTML_HEADING.match(stripped):
            continue
        marker = _MARKER.match(stripped)
        if marker and marker.group(1).lower() == "chapter":
            continue
        return True
    return False


def _choose_chapter_boundaries(
    lines: list[str],
    headings: list[_Heading],
    markers: list[_Marker],
    content_start: int,
    chapter_heading_level: int | None,
) -> list[_Boundary]:
    chapter_markers = [marker for marker in markers if marker.kind == "chapter"]
    if chapter_markers:
        boundaries: list[_Boundary] = []
        for position, marker in enumerate(chapter_markers):
            next_marker = (
                chapter_markers[position + 1].line_index
                if position + 1 < len(chapter_markers)
                else len(lines)
            )
            next_heading = next(
                (
                    heading
                    for heading in headings
                    if marker.line_index < heading.line_index < next_marker
                ),
                None,
            )
            boundaries.append(
                _Boundary(
                    marker.line_index,
                    marker.line_index + 1,
                    marker.title or (next_heading.title if next_heading else None),
                    marker.uid,
                )
            )
        return boundaries

    usable_headings = [heading for heading in headings if heading.line_index >= content_start]
    if chapter_heading_level is not None:
        if not 1 <= chapter_heading_level <= 6:
            raise MarkdownParseError("chapter_heading_level deve estar entre 1 e 6")
        chosen = [h for h in usable_headings if h.level == chapter_heading_level]
    else:
        semantic = [h for h in usable_headings if _SEMANTIC_CHAPTER.match(h.title)]
        if len(semantic) >= 2:
            chosen = semantic
        else:
            counts = {
                level: sum(heading.level == level for heading in usable_headings)
                for level in range(1, 7)
            }
            h1_count = counts[1]
            h2_headings = [heading for heading in usable_headings if heading.level == 2]
            numbered_h2 = sum(bool(_NUMBERED_HEADING.match(h.title)) for h in h2_headings)
            structural_h1 = sum(
                bool(_STRUCTURAL_HEADING.match(h.title))
                for h in usable_headings
                if h.level == 1
            )
            h2_looks_like_chapters = len(h2_headings) >= 3 and (
                numbered_h2 / len(h2_headings) >= 0.6
                or (h1_count > 0 and structural_h1 / h1_count >= 0.6)
            )
            if h1_count >= 2 and not h2_looks_like_chapters:
                selected_level = 1
            elif h2_looks_like_chapters:
                selected_level = 2
            else:
                shallow_levels = [level for level in (1, 2) if counts[level] >= 2]
                eligible_levels = shallow_levels or [
                    level for level in range(3, 7) if counts[level] >= 2
                ]
                selected_level = (
                    max(eligible_levels, key=lambda level: (counts[level], -level))
                    if eligible_levels
                    else (usable_headings[0].level if usable_headings else 1)
                )
            chosen = [h for h in usable_headings if h.level == selected_level]

    if not chosen:
        return [_Boundary(content_start, content_start, "Documento", None)]

    boundaries = [_Boundary(h.line_index, h.line_index, h.title, None) for h in chosen]
    if _has_meaningful_content(lines, content_start, chosen[0].line_index):
        boundaries.insert(0, _Boundary(content_start, content_start, "Preâmbulo", None))
    return boundaries


def _unique_keys(titles: list[str | None], prefix: str) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for index, title in enumerate(titles, start=1):
        base = slugify(title or "", fallback=f"{prefix}-{index:03d}")
        seen[base] = seen.get(base, 0) + 1
        result.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
    return result


def _paragraph_ranges(content: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    paragraph_start: int | None = None
    offset = 0
    for line in content.splitlines(keepends=True):
        next_offset = offset + len(line)
        if line.strip():
            if paragraph_start is None:
                paragraph_start = offset
        elif paragraph_start is not None:
            ranges.append((paragraph_start, offset))
            paragraph_start = None
        offset = next_offset
    if paragraph_start is not None:
        ranges.append((paragraph_start, len(content)))
    return ranges


def _build_passages(
    content: str,
    scene_start_line: int,
    *,
    target_words: int,
    overlap_paragraphs: int,
) -> tuple[PassageDraft, ...]:
    if target_words <= 0:
        raise MarkdownParseError("passage_target_words deve ser positivo")
    if overlap_paragraphs < 0:
        raise MarkdownParseError("passage_overlap_paragraphs não pode ser negativo")
    paragraphs = _paragraph_ranges(content)
    if not paragraphs and content:
        paragraphs = [(0, len(content))]
    passages: list[PassageDraft] = []
    start_index = 0
    while start_index < len(paragraphs):
        end_index = start_index
        words = 0
        while end_index < len(paragraphs):
            paragraph = content[paragraphs[end_index][0] : paragraphs[end_index][1]]
            paragraph_words = len(_WORD.findall(paragraph))
            if end_index > start_index and words + paragraph_words > target_words:
                break
            words += paragraph_words
            end_index += 1
            if words >= target_words:
                break

        start_offset = paragraphs[start_index][0]
        end_offset = paragraphs[end_index - 1][1]
        passage_content = content[start_offset:end_offset]
        start_line = scene_start_line + content.count("\n", 0, start_offset)
        end_line = scene_start_line + content.count("\n", 0, max(start_offset, end_offset - 1))
        passages.append(
            PassageDraft(
                ordinal=len(passages),
                start_offset=start_offset,
                end_offset=end_offset,
                start_line=start_line,
                end_line=end_line,
                content=passage_content,
                content_sha256=hashlib.sha256(passage_content.encode("utf-8")).hexdigest(),
                token_count=len(_WORD.findall(passage_content)),
            )
        )
        if end_index >= len(paragraphs):
            break
        next_start = end_index - min(overlap_paragraphs, end_index - start_index - 1)
        start_index = max(start_index + 1, next_start)
    return tuple(passages)


def _scene_segments(
    lines: list[str],
    chapter_start: int,
    chapter_end: int,
    markers: list[_Marker],
) -> list[tuple[int, int, str | None, str | None]]:
    scene_markers = [
        marker
        for marker in markers
        if marker.kind == "scene" and chapter_start <= marker.line_index < chapter_end
    ]
    segments: list[tuple[int, int, str | None, str | None]] = []
    if scene_markers:
        if _has_scene_content(lines, chapter_start, scene_markers[0].line_index):
            segments.append((chapter_start, scene_markers[0].line_index, None, None))
        for index, marker in enumerate(scene_markers):
            end = (
                scene_markers[index + 1].line_index
                if index + 1 < len(scene_markers)
                else chapter_end
            )
            if _has_meaningful_content(lines, marker.line_index + 1, end):
                segments.append((marker.line_index + 1, end, marker.uid, marker.title))
        return segments

    implicit_start = chapter_start
    first_line = lines[chapter_start].rstrip("\r\n") if chapter_start < chapter_end else ""
    if _ATX_HEADING.match(first_line) or _HTML_HEADING.match(first_line):
        # O título já está em scene_title. Mantê-lo fora do hash evita que uma
        # simples renomeação invalide conteúdo, diffs e embeddings.
        implicit_start += 1
    breaks = [
        index
        for index in range(implicit_start + 1, chapter_end - 1)
        if _HORIZONTAL_RULE.match(lines[index].strip())
    ]
    start = implicit_start
    for boundary in breaks + [chapter_end]:
        if _has_meaningful_content(lines, start, boundary):
            segments.append((start, boundary, None, None))
        start = boundary + 1
    return segments or [(implicit_start, chapter_end, None, None)]


def parse_markdown(
    source_path: str | Path,
    *,
    chapter_heading_level: int | None = None,
    passage_target_words: int = 350,
    passage_overlap_paragraphs: int = 1,
) -> ParsedManuscript:
    """Lê e segmenta um manuscrito sem modificar o arquivo canônico."""

    path = Path(source_path).expanduser().resolve()
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise MarkdownParseError(f"manuscrito não está em UTF-8: {path}") from exc
    lines = content.splitlines(keepends=True)
    if not lines:
        raise MarkdownParseError("manuscrito vazio")

    content_start = _frontmatter_end(lines)
    headings, markers = _scan_structure(lines)
    boundaries = _choose_chapter_boundaries(
        lines, headings, markers, content_start, chapter_heading_level
    )
    chapter_keys = _unique_keys([boundary.title for boundary in boundaries], "chapter")
    chapters: list[ChapterDraft] = []
    for chapter_ordinal, boundary in enumerate(boundaries):
        chapter_end = (
            boundaries[chapter_ordinal + 1].line_index
            if chapter_ordinal + 1 < len(boundaries)
            else len(lines)
        )
        segment_start = boundary.content_start
        segments = _scene_segments(lines, segment_start, chapter_end, markers)
        scene_titles: list[str | None] = []
        for start, _end, _uid, explicit_title in segments:
            heading = next((h for h in headings if h.line_index == start), None)
            scene_titles.append(explicit_title or (heading.title if heading else boundary.title))
        scene_keys = _unique_keys(scene_titles, "scene")
        scenes: list[SceneDraft] = []
        for scene_ordinal, (start, end, declared_uid, _explicit_title) in enumerate(segments):
            if declared_uid is not None and len(declared_uid) < 16:
                raise MarkdownParseError(
                    f"scene UID curto demais na linha {start}: {declared_uid!r}"
                )
            scene_content = "".join(lines[start:end]).rstrip()
            start_line = start + 1
            end_line = max(start_line, end)
            digest = hashlib.sha256(scene_content.encode("utf-8")).hexdigest()
            passages = _build_passages(
                scene_content,
                start_line,
                target_words=passage_target_words,
                overlap_paragraphs=passage_overlap_paragraphs,
            )
            scenes.append(
                SceneDraft(
                    ordinal=scene_ordinal,
                    stable_key=scene_keys[scene_ordinal],
                    declared_uid=declared_uid,
                    title=scene_titles[scene_ordinal],
                    start_line=start_line,
                    end_line=end_line,
                    content=scene_content,
                    content_sha256=digest,
                    token_count=len(_WORD.findall(scene_content)),
                    passages=passages,
                )
            )
        chapter_start_line = segment_start + 1
        chapter_end_line = max(chapter_start_line, chapter_end)
        if boundary.declared_uid is not None and len(boundary.declared_uid) < 16:
            raise MarkdownParseError(
                f"chapter UID curto demais na linha {boundary.line_index + 1}: "
                f"{boundary.declared_uid!r}"
            )
        chapters.append(
            ChapterDraft(
                ordinal=chapter_ordinal,
                stable_key=chapter_keys[chapter_ordinal],
                declared_uid=boundary.declared_uid,
                title=boundary.title,
                start_line=chapter_start_line,
                end_line=chapter_end_line,
                scenes=tuple(scenes),
            )
        )

    return ParsedManuscript(
        source_path=path,
        content_sha256=hashlib.sha256(raw).hexdigest(),
        byte_size=len(raw),
        chapters=tuple(chapters),
    )
