"""Prova editorial para capítulos integralmente ilustrados.

O módulo transforma o contrato de ``plano_ilustracoes.yaml`` em páginas de
livro: uma abertura ímpar, três ou mais spreads com texto integrado e uma página
de reflexão. A saída possui MediaBox com sangria e TrimBox no formato de corte.
"""

from __future__ import annotations

import html
import re
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml
import cv2
import numpy as np
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, FloatObject, NameObject
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import portrait
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph


PAPER = HexColor("#F4EBD8")
INK = HexColor("#2E2923")
ACCENT = HexColor("#8A3F2A")
MUTED = HexColor("#675D52")

THEME_PRESETS = {
    "creme": {
        "paper": "#F4EBD8", "ink": "#2E2923",
        "accent": "#8A3F2A", "muted": "#675D52",
    },
    "branco": {
        "paper": "#FAF9F5", "ink": "#252525",
        "accent": "#6F3B32", "muted": "#625E59",
    },
}


@dataclass
class Chapter:
    order: int
    title: str
    attribution: str
    narrative: list[str]
    reflection: list[str]
    pages: list[int]
    virtue: str
    virtue_ideogram: str
    virtue_reading: str
    scenes: list[dict]


def _register_fonts() -> None:
    fonts = {
        "Editorial": "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "Editorial-Bold": "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "Editorial-Italic": "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
        "EditorialSans": "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    }
    for name, path in fonts.items():
        if name not in pdfmetrics.getRegisteredFontNames() and Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))


def _clean(text: str) -> str:
    text = re.sub(r"!\[[^]]*]\([^)]*\)", "", text)
    text = re.sub(r"[*_`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _paragraphs(block: str) -> list[str]:
    result: list[str] = []
    for raw in re.split(r"\n\s*\n", block):
        value = " ".join(line.strip() for line in raw.splitlines() if line.strip())
        value = _clean(value)
        if not value or value == "---" or value.startswith((":::", "![")):
            continue
        result.append(value)
    return result


def _parse_manuscript(path: Path) -> dict[str, dict]:
    source = path.read_text(encoding="utf-8")
    if source.startswith("---"):
        source = source.split("---", 2)[-1]
    sections = re.split(r"(?m)^#\s+", source)[1:]
    parsed: dict[str, dict] = {}
    for section in sections:
        title, _, body = section.partition("\n")
        title = title.strip()
        attribution = ""
        match = re.search(r"(?m)^>\s*(.+)$", body)
        if match:
            attribution = _clean(match.group(1))
        body = re.sub(r"(?ms)^:::\s*(?:moldura|pagina-cheia).*?^:::\s*$", "", body)
        body = re.sub(r"(?m)^>\s*.+$", "", body)
        narrative_block, marker, reflection_block = body.partition("## Reflexão")
        parsed[title] = {
            "attribution": attribution,
            "narrative": _paragraphs(narrative_block),
            "reflection": _paragraphs(reflection_block) if marker else [],
        }
    return parsed


def _configure_palette(path: Path) -> str:
    """Aplica o tema declarado pela obra, com sobrescritas hex opcionais."""
    global PAPER, INK, ACCENT, MUTED
    source = path.read_text(encoding="utf-8")
    metadata: dict = {}
    if source.startswith("---"):
        metadata = yaml.safe_load(source.split("---", 2)[1]) or {}
    theme_name = str(metadata.get("theme", "Creme"))
    preset = dict(THEME_PRESETS.get(theme_name.casefold(), THEME_PRESETS["creme"]))
    overrides = metadata.get("layout_palette") or {}
    for key in ("paper", "ink", "accent", "muted"):
        if overrides.get(key):
            preset[key] = overrides[key]
    PAPER = HexColor(preset["paper"])
    INK = HexColor(preset["ink"])
    ACCENT = HexColor(preset["accent"])
    MUTED = HexColor(preset["muted"])
    return theme_name


def _load_chapters(book_dir: Path, selected: set[int]) -> tuple[dict, list[Chapter]]:
    plan = yaml.safe_load((book_dir / "plano_ilustracoes.yaml").read_text(encoding="utf-8"))
    manuscript = _parse_manuscript(book_dir / "texto_revisado.md")
    book_config_path = book_dir / "book_config.yaml"
    book_config = yaml.safe_load(book_config_path.read_text(encoding="utf-8")) if book_config_path.exists() else {}
    virtue_data = {
        int(item["id"]): item for item in book_config.get("historias", [])
    }
    chapters: list[Chapter] = []
    for item in plan.get("capitulos", []):
        order = int(item["ordem"])
        if order not in selected:
            continue
        title = item["titulo"]
        if title not in manuscript:
            raise ValueError(f"Capítulo não encontrado no manuscrito: {title}")
        scenes = item.get("cenas", [])
        if len(scenes) < 4 or scenes[0].get("tipo") != "abertura" or any(
            scene.get("tipo") != "spread" for scene in scenes[1:]
        ):
            raise ValueError(
                f"O Conto {order} precisa de uma abertura e no mínimo três spreads"
            )
        expected_pages = 2 + 2 * (len(scenes) - 1)
        declared_start, declared_end = map(int, item["paginas"])
        if declared_end - declared_start + 1 != expected_pages:
            raise ValueError(
                f"O Conto {order} possui {len(scenes) - 1} spreads e precisa ocupar "
                f"{expected_pages} páginas, incluindo abertura e reflexão"
            )
        blocked = [s["id"] for s in scenes if s.get("status") not in {"aprovada_para_layout", "arte_aprovada"}]
        if blocked:
            raise ValueError("Artes ainda não aprovadas para layout: " + ", ".join(blocked))
        pages = list(range(int(item["paginas"][0]), int(item["paginas"][1]) + 1))
        reflection = manuscript[title]["reflection"]
        metadata = virtue_data.get(order, {})
        reflection_text = " ".join(reflection)
        virtue_match = re.search(r"ensina (?:a|o)\s+([\wÀ-ÿ-]+)", reflection_text, flags=re.IGNORECASE)
        virtue = str(metadata.get("virtude_tomista") or (virtue_match.group(1) if virtue_match else "Reflexão")).upper()
        chapters.append(Chapter(
            order=order,
            title=title,
            attribution=manuscript[title]["attribution"],
            narrative=manuscript[title]["narrative"],
            reflection=reflection,
            pages=pages,
            virtue=virtue,
            virtue_ideogram=str(metadata.get("ideograma_virtude", "德")),
            virtue_reading=str(metadata.get("leitura_ideograma", "dé")),
            scenes=scenes,
        ))
    if not chapters:
        raise ValueError("Nenhum capítulo selecionado")
    return plan, chapters


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def _take_opening(paragraphs: list[str]) -> tuple[list[str], list[str]]:
    """A abertura recebe somente o primeiro parágrafo para preservar a arte."""
    if not paragraphs:
        return [], []
    return [paragraphs[0]], list(paragraphs[1:])


def _balanced_groups(paragraphs: list[str], count: int) -> list[list[str]]:
    groups: list[list[str]] = []
    remaining = list(paragraphs)
    for index in range(count):
        slots = count - index
        if not remaining:
            groups.append([])
            continue
        target = sum(_word_count(p) for p in remaining) / slots
        group: list[str] = []
        words = 0
        while remaining:
            minimum_left = slots - 1
            if group and words >= target and len(remaining) >= minimum_left:
                break
            group.append(remaining.pop(0))
            words += _word_count(group[-1])
            if len(remaining) == minimum_left:
                break
        groups.append(group)
    if remaining:
        groups[-1].extend(remaining)
    return groups


def _draw_image_cover(c: canvas.Canvas, image: Image.Image, width: float, height: float) -> None:
    """Recorta para a página e incorpora uma cópia JPEG leve de 180 dpi."""
    iw, ih = image.size
    target_ratio = width / height
    source_ratio = iw / ih
    if source_ratio > target_ratio:
        crop_w = int(ih * target_ratio)
        left = (iw - crop_w) // 2
        image = image.crop((left, 0, left + crop_w, ih))
    elif source_ratio < target_ratio:
        crop_h = int(iw / target_ratio)
        top = (ih - crop_h) // 2
        image = image.crop((0, top, iw, top + crop_h))
    px_w = max(1, int(width / 72 * 180))
    px_h = max(1, int(height / 72 * 180))
    image = image.resize((px_w, px_h), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=91, optimize=True, progressive=True)
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), 0, 0, width, height, mask="auto")


def _gradient(c: canvas.Canvas, width: float, height: float, top: bool = True) -> None:
    steps = 36
    band = 84 * mm
    for i in range(steps):
        alpha = 0.94 * (1 - i / steps) ** 1.7
        y = height - (i + 1) * band / steps if top else i * band / steps
        c.setFillColor(Color(PAPER.red, PAPER.green, PAPER.blue, alpha=alpha))
        c.rect(0, y, width, band / steps + 0.3, stroke=0, fill=1)


def _draw_opener_field(c: canvas.Canvas, width: float, height: float,
                       opaque_bottom: float, fade_depth: float = 18 * mm) -> None:
    """Protege todo o cabeçalho e dissolve o papel suavemente na ilustração."""
    dpi = 240
    px_w = max(8, int(round(width / 72 * dpi)))
    px_h = max(8, int(round(height / 72 * dpi)))
    solid_end = int(round((height - opaque_bottom) / height * px_h))
    fade_px = max(8, int(round(fade_depth / 72 * dpi)))

    rows = np.arange(px_h, dtype=np.float32)
    progress = np.clip((rows - solid_end) / fade_px, 0.0, 1.0)
    progress = progress * progress * (3.0 - 2.0 * progress)
    alpha_rows = np.clip(247.0 * (1.0 - progress), 0, 247).astype(np.uint8)

    rgba = np.empty((px_h, px_w, 4), dtype=np.uint8)
    rgba[:, :, 0] = int(round(PAPER.red * 255))
    rgba[:, :, 1] = int(round(PAPER.green * 255))
    rgba[:, :, 2] = int(round(PAPER.blue * 255))
    rgba[:, :, 3] = alpha_rows[:, None]
    field = Image.fromarray(rgba, mode="RGBA")
    buffer = BytesIO()
    field.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), 0, 0, width, height, mask="auto")


def _as_markup(paragraphs: Iterable[str]) -> str:
    chunks = []
    for p in paragraphs:
        escaped = html.escape(_clean(p))
        chunks.append(escaped)
    return "<br/><br/>".join(chunks)


def _fit_paragraph(markup: str, width: float, height: float, max_size: float = 9.6) -> tuple[Paragraph, float, float, float]:
    sizes = [max_size, max_size - 0.25, max_size - 0.5, max_size - 0.75]
    for size in sizes:
        style = ParagraphStyle(
            "overlay", fontName="Editorial", fontSize=size, leading=size * 1.34,
            textColor=INK, alignment=TA_LEFT, splitLongWords=False,
            allowWidows=0, allowOrphans=0,
        )
        paragraph = Paragraph(markup, style)
        used_w, used_h = paragraph.wrap(width, height)
        if used_h <= height:
            return paragraph, used_w, used_h, size
    return paragraph, used_w, used_h, size


def _split_for_two_panels(paragraphs: list[str]) -> tuple[list[str], list[str]]:
    """Divide em fronteira de parágrafo, equilibrando a contagem de palavras."""
    if len(paragraphs) < 2:
        return paragraphs, []
    total = sum(_word_count(p) for p in paragraphs)
    best_index = 1
    best_delta = total
    running = 0
    for index, paragraph in enumerate(paragraphs[:-1], 1):
        running += _word_count(paragraph)
        delta = abs(total - 2 * running)
        if delta < best_delta:
            best_index, best_delta = index, delta
    return paragraphs[:best_index], paragraphs[best_index:]


def _visual_complexity(image: Image.Image, position: str, fraction: float) -> float:
    """Estima detalhe e presença de rostos na faixa candidata da página."""
    rgb = np.asarray(image.convert("RGB"))
    height = rgb.shape[0]
    band = max(1, min(height, int(height * fraction)))
    region = rgb[:band] if position == "top" else rgb[height - band:]
    gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
    edge_density = float(np.mean(cv2.Canny(gray, 70, 150) > 0))
    contrast = float(np.std(gray) / 255.0)
    face_penalty = 0.0
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if not detector.empty():
        faces = detector.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(24, 24))
        face_penalty = min(0.45, len(faces) * 0.16)
    return edge_density * 1.8 + contrast * 0.55 + face_penalty


def _draw_soft_veil(c: canvas.Canvas, x: float, y: float, width: float, height: float) -> None:
    """Cria apoio de leitura com máscara alfa contínua, sem faixas vetoriais."""
    dpi = 240
    px_w = max(8, int(round(width / 72 * dpi)))
    px_h = max(8, int(round(height / 72 * dpi)))
    edge_x = max(8, int(round(4.8 * mm / 72 * dpi)))
    edge_y = max(8, int(round(3.2 * mm / 72 * dpi)))

    yy, xx = np.ogrid[:px_h, :px_w]
    dist_x = np.minimum(xx, px_w - 1 - xx).astype(np.float32)
    dist_y = np.minimum(yy, px_h - 1 - yy).astype(np.float32)
    sx = np.clip(dist_x / edge_x, 0.0, 1.0)
    sy = np.clip(dist_y / edge_y, 0.0, 1.0)
    # Smoothstep dá uma transição contínua até a ilustração.
    sx = sx * sx * (3.0 - 2.0 * sx)
    sy = sy * sy * (3.0 - 2.0 * sy)
    alpha = np.clip(202.0 * sx * sy, 0, 202).astype(np.uint8)

    rgba = np.empty((px_h, px_w, 4), dtype=np.uint8)
    rgba[:, :, 0] = int(round(PAPER.red * 255))
    rgba[:, :, 1] = int(round(PAPER.green * 255))
    rgba[:, :, 2] = int(round(PAPER.blue * 255))
    rgba[:, :, 3] = alpha

    veil = Image.fromarray(rgba, mode="RGBA")
    buffer = BytesIO()
    veil.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), x, y, width, height, mask="auto")


def _draw_panel_at(c: canvas.Canvas, paragraphs: list[str], page_w: float, page_h: float,
                   bleed: float, position: str, image: Image.Image) -> float:
    margin = bleed + 8.0 * mm
    panel_w = page_w - 2 * margin
    max_text_h = 69 * mm
    paragraph, _, used_h, font_size = _fit_paragraph(
        _as_markup(paragraphs), panel_w, max_text_h, max_size=9.6,
    )
    # O véu se estende além da mancha textual para que o texto não dispute
    # visualmente com a região esmaecida das bordas.
    padding_x = 5.2 * mm
    padding_y = 4.6 * mm
    veil_h = used_h + 2 * padding_y
    x = margin - padding_x
    if position == "top":
        y = page_h - bleed - 7.5 * mm - veil_h
    else:
        y = bleed + 10.5 * mm
    _draw_soft_veil(c, x, y, panel_w + 2 * padding_x, veil_h)
    paragraph.drawOn(c, margin, y + padding_y)
    return font_size


def _draw_text_panel(c: canvas.Canvas, paragraphs: list[str], image: Image.Image,
                     page_w: float, page_h: float, bleed: float,
                     layout: str = "auto") -> None:
    """Compõe o texto em ``auto``, ``top``, ``bottom`` ou ``split``.

    O modo automático continua sendo a regra geral. A direção editorial por
    página permite registrar uma correção aprovada quando a análise visual
    detectar que o texto disputa um rosto ou outro elemento narrativo.
    """
    if not paragraphs:
        return
    layout = str(layout or "auto").lower()
    if layout not in {"auto", "top", "bottom", "split"}:
        raise ValueError(f"Distribuição de texto desconhecida: {layout}")
    margin = bleed + 8.0 * mm
    panel_w = page_w - 2 * margin
    probe, _, used_h, _ = _fit_paragraph(_as_markup(paragraphs), panel_w, 69 * mm, max_size=9.6)
    del probe
    should_split = len(paragraphs) >= 2 and (
        layout == "split"
        or (layout == "auto" and (_word_count(" ".join(paragraphs)) >= 112 or used_h > 51 * mm))
    )
    top_group, bottom_group = _split_for_two_panels(paragraphs) if should_split else (paragraphs, [])
    if bottom_group:
        _draw_panel_at(c, top_group, page_w, page_h, bleed, "top", image)
        _draw_panel_at(c, bottom_group, page_w, page_h, bleed, "bottom", image)
        return
    if layout in {"top", "bottom"}:
        _draw_panel_at(c, paragraphs, page_w, page_h, bleed, layout, image)
        return
    estimated_fraction = min(0.46, max(0.16, (used_h + 8 * mm) / page_h))
    top_score = _visual_complexity(image, "top", estimated_fraction)
    bottom_score = _visual_complexity(image, "bottom", estimated_fraction)
    position = "top" if top_score <= bottom_score else "bottom"
    _draw_panel_at(c, paragraphs, page_w, page_h, bleed, position, image)


def _folio(c: canvas.Canvas, number: int, page_w: float, bleed: float) -> None:
    x = bleed + 8 * mm if number % 2 == 0 else page_w - bleed - 8 * mm
    y = bleed + 5.8 * mm
    radius = 3.5 * mm
    c.saveState()
    c.setFillColor(Color(PAPER.red, PAPER.green, PAPER.blue, alpha=0.88))
    c.setStrokeColor(Color(ACCENT.red, ACCENT.green, ACCENT.blue, alpha=0.58))
    c.setLineWidth(0.45)
    c.circle(x, y, radius, stroke=1, fill=1)
    c.setFont("EditorialSans", 6.6)
    c.setFillColor(Color(INK.red, INK.green, INK.blue, alpha=0.86))
    c.drawCentredString(x, y - 2.15, str(number))
    c.restoreState()


def _draw_opener(c: canvas.Canvas, chapter: Chapter, image: Image.Image, opening: list[str],
                 page_w: float, page_h: float, bleed: float) -> None:
    _draw_image_cover(c, image, page_w, page_h)
    safe_x = bleed + 10 * mm
    safe_w = page_w - 2 * safe_x
    title_style = ParagraphStyle(
        "title", fontName="Editorial-Bold", fontSize=17.5, leading=19.8,
        textColor=INK, spaceAfter=0,
    )
    title = Paragraph(html.escape(chapter.title), title_style)
    _, title_h = title.wrap(safe_w, 45 * mm)
    marker_y = page_h - bleed - 8.5 * mm
    title_y = page_h - bleed - 12.2 * mm - title_h
    source_style = ParagraphStyle(
        "source", fontName="EditorialSans", fontSize=6.0, leading=7.5,
        textColor=MUTED,
    )
    source = Paragraph(html.escape(chapter.attribution), source_style)
    _, source_h = source.wrap(safe_w, 16 * mm)
    source_y = title_y - 1.8 * mm - source_h
    body_h = 36 * mm
    paragraph, _, used_h, _ = _fit_paragraph(_as_markup(opening), safe_w, body_h, max_size=9.2)
    body_y = source_y - 2.8 * mm - used_h
    _draw_opener_field(c, page_w, page_h, body_y - 1.5 * mm, fade_depth=11 * mm)
    # Marcador editorial sóbrio com pequeno selo, sem lettering temático literal.
    c.saveState()
    label_size = 6.8
    label_spacing = 1.15
    label = c.beginText(safe_x, marker_y)
    label.setFont("EditorialSans", label_size)
    label.setCharSpace(label_spacing)
    label.setFillColor(ACCENT)
    label.textOut("CONTO")
    c.drawText(label)
    label_w = pdfmetrics.stringWidth("CONTO", "EditorialSans", label_size) + 4 * label_spacing
    seal_x = safe_x + label_w + 2.1 * mm
    seal_size = 5.2 * mm
    seal_y = marker_y - 1.55 * mm
    c.setFillColor(ACCENT)
    c.roundRect(seal_x, seal_y, seal_size, seal_size, 0.65 * mm, stroke=0, fill=1)
    c.setFillColor(PAPER)
    c.setFont("Editorial-Bold", 6.2)
    c.drawCentredString(seal_x + seal_size / 2, seal_y + 1.45 * mm, f"{chapter.order:02d}")
    c.restoreState()
    title.drawOn(c, safe_x, title_y)
    source.drawOn(c, safe_x, source_y)
    paragraph.drawOn(c, safe_x, body_y)
    _folio(c, chapter.pages[0], page_w, bleed)


def _draw_spread_pages(c: canvas.Canvas, chapter: Chapter, scene: dict, groups: list[list[str]],
                       page_numbers: list[int], page_w: float, page_h: float, bleed: float) -> None:
    source = Image.open(scene["_absolute_path"]).convert("RGB")
    midpoint = source.width // 2
    halves = [source.crop((0, 0, midpoint, source.height)), source.crop((midpoint, 0, source.width, source.height))]
    page_layouts = list(scene.get("distribuicao_texto_paginas", ["auto", "auto"]))
    if len(page_layouts) != 2:
        raise ValueError(
            f"A cena {scene.get('id', '<sem id>')} precisa de duas distribuições de texto"
        )
    for half, text, page_number, text_layout in zip(halves, groups, page_numbers, page_layouts):
        _draw_image_cover(c, half, page_w, page_h)
        _draw_text_panel(c, text, half, page_w, page_h, bleed, text_layout)
        _folio(c, page_number, page_w, bleed)
        c.showPage()


def _draw_reflection(c: canvas.Canvas, chapter: Chapter, page_w: float, page_h: float, bleed: float) -> None:
    c.setFillColor(PAPER)
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)
    safe_x = bleed + 13 * mm
    safe_w = page_w - 2 * safe_x
    top = page_h - bleed - 18 * mm
    c.setFillColor(ACCENT)
    c.setFont("EditorialSans", 7.2)
    c.drawString(safe_x, top, f"VIRTUDE  ·  {chapter.virtue}")
    c.setFillColor(INK)
    c.setFont("Editorial-Bold", 20)
    c.drawString(safe_x, top - 13 * mm, "Reflexão")
    c.setStrokeColor(Color(ACCENT.red, ACCENT.green, ACCENT.blue, alpha=0.55))
    c.setLineWidth(0.8)
    c.line(safe_x, top - 18 * mm, page_w - safe_x, top - 18 * mm)
    markup = _as_markup(chapter.reflection)
    paragraph, _, used_h, _ = _fit_paragraph(markup, safe_w, 104 * mm, max_size=10.0)
    paragraph.drawOn(c, safe_x, top - 25 * mm - used_h)
    # Assinatura cultural vetorial: ideograma da virtude, sem medalhão genérico.
    mark_x = page_w - safe_x - 9 * mm
    mark_y = bleed + 17 * mm
    c.saveState()
    c.setStrokeColor(Color(ACCENT.red, ACCENT.green, ACCENT.blue, alpha=0.42))
    c.setLineWidth(0.55)
    c.line(mark_x - 8 * mm, mark_y + 19 * mm, mark_x + 8 * mm, mark_y + 19 * mm)
    c.line(mark_x, mark_y - 3 * mm, mark_x, mark_y + 1.5 * mm)
    c.setFillColor(Color(ACCENT.red, ACCENT.green, ACCENT.blue, alpha=0.88))
    c.setFont("EditorialSans", 22)
    c.drawCentredString(mark_x, mark_y + 4 * mm, chapter.virtue_ideogram)
    c.setFont("EditorialSans", 5.8)
    reading = f"{chapter.virtue_reading.upper()}  ·  {chapter.virtue}"
    c.drawCentredString(mark_x, mark_y, reading)
    c.restoreState()
    _folio(c, chapter.pages[-1], page_w, bleed)


def _set_print_boxes(source: Path, destination: Path, trim_w: float, trim_h: float, bleed: float) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    trim = ArrayObject([
        FloatObject(float(bleed)), FloatObject(float(bleed)),
        FloatObject(float(bleed + trim_w)), FloatObject(float(bleed + trim_h)),
    ])
    for page in reader.pages:
        page[NameObject("/TrimBox")] = trim
        page[NameObject("/BleedBox")] = ArrayObject([
            FloatObject(0), FloatObject(0),
            FloatObject(float(trim_w + 2 * bleed)), FloatObject(float(trim_h + 2 * bleed)),
        ])
        writer.add_page(page)
    writer.page_layout = "/TwoPageRight"
    with destination.open("wb") as stream:
        writer.write(stream)


def generate_illustrated_proof(book_dir: Path, chapters: list[int], output: Path) -> Path:
    """Gera uma prova de capítulos ilustrados e retorna o PDF final."""
    _register_fonts()
    _configure_palette(book_dir / "texto_revisado.md")
    plan, selected = _load_chapters(book_dir, set(chapters))
    trim_w_mm, trim_h_mm = plan["miolo"]["formato_corte_mm"]
    bleed_mm = float(plan["miolo"]["sangria_mm"])
    trim_w, trim_h, bleed = trim_w_mm * mm, trim_h_mm * mm, bleed_mm * mm
    page_w, page_h = trim_w + 2 * bleed, trim_h + 2 * bleed
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".working.pdf")
    c = canvas.Canvas(str(temporary), pagesize=portrait((page_w, page_h)), pageCompression=1)
    c.setTitle("Prova editorial — capítulos ilustrados")
    for chapter in selected:
        for scene in chapter.scenes:
            path = book_dir / scene["arquivo"]
            if not path.exists():
                raise FileNotFoundError(path)
            scene["_absolute_path"] = str(path)
        opening, remaining = _take_opening(chapter.narrative)
        has_custom = all("paragrafos" in scene for scene in chapter.scenes[1:])
        if has_custom:
            groups = []
            for scene in chapter.scenes[1:]:
                pg_left_idx, pg_right_idx = scene["paragrafos"]
                left_pars = [remaining[i] for i in pg_left_idx if i < len(remaining)]
                right_pars = [remaining[i] for i in pg_right_idx if i < len(remaining)]
                groups.extend([left_pars, right_pars])
        else:
            spread_count = len(chapter.scenes) - 1
            groups = _balanced_groups(remaining, spread_count * 2)
        opener = Image.open(chapter.scenes[0]["_absolute_path"]).convert("RGB")
        _draw_opener(c, chapter, opener, opening, page_w, page_h, bleed)
        c.showPage()
        for spread_index, scene in enumerate(chapter.scenes[1:]):
            offset = spread_index * 2
            _draw_spread_pages(
                c, chapter, scene, groups[offset:offset + 2],
                chapter.pages[1 + offset:3 + offset], page_w, page_h, bleed,
            )
        _draw_reflection(c, chapter, page_w, page_h, bleed)
        c.showPage()
    c.save()
    _set_print_boxes(temporary, output, trim_w, trim_h, bleed)
    temporary.unlink(missing_ok=True)
    return output
