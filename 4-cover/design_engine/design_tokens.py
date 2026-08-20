"""
4-cover/design_engine/design_tokens.py
--------------------------------------
Gerenciador de Tokens de Design: Biblioteca Expandida de Fontes e Paletas Editoriais.
"""

from typing import Dict, Any

COLOR_PALETTES = {
    "nanquim": {
        "bg_color": "#141214",
        "gold_color": "#d4af37",
        "soft_gold": "#f0e6d2",
        "text_light": "#ffffff",
        "text_subtle": "#cccccc",
        "box_bg": "rgba(255, 255, 255, 0.03)",
        "box_border": "rgba(212, 175, 55, 0.2)"
    },
    "vinho": {
        "bg_color": "#2a1215",
        "gold_color": "#e8c3b9",
        "soft_gold": "#f4e3df",
        "text_light": "#ffffff",
        "text_subtle": "#e0c0c5",
        "box_bg": "rgba(255, 255, 255, 0.04)",
        "box_border": "rgba(232, 195, 185, 0.25)"
    },
    "marinho": {
        "bg_color": "#0f172a",
        "gold_color": "#cbd5e1",
        "soft_gold": "#e2e8f0",
        "text_light": "#ffffff",
        "text_subtle": "#94a3b8",
        "box_bg": "rgba(255, 255, 255, 0.03)",
        "box_border": "rgba(203, 213, 225, 0.2)"
    },
    "creme": {
        "bg_color": "#f8f5ee",
        "gold_color": "#8c6d1f",
        "soft_gold": "#5c4a15",
        "text_light": "#1a1a1a",
        "text_subtle": "#4a4a4a",
        "box_bg": "rgba(0, 0, 0, 0.03)",
        "box_border": "rgba(140, 109, 31, 0.2)"
    },
    "esmeralda": {
        "bg_color": "#0b231a",
        "gold_color": "#d4af37",
        "soft_gold": "#d1e7dd",
        "text_light": "#ffffff",
        "text_subtle": "#a3cfbb",
        "box_bg": "rgba(255, 255, 255, 0.03)",
        "box_border": "rgba(212, 175, 55, 0.25)"
    }
}

# Biblioteca Expandida de Fontes por Gênero Editorial
FONT_THEMES = {
    "imperial_oriental": {
        "google_fonts_url": "family=Cinzel+Decorative:wght@700;900&family=Cinzel:wght@700;900&family=Cormorant+Garamond:ital,wght@0,600;1,400&family=Montserrat:wght@500;700",
        "font_title": "'Cinzel Decorative', 'Cinzel', serif",
        "font_body": "'Cormorant Garamond', serif",
        "font_tag": "'Montserrat', sans-serif"
    },
    "romance_classico": {
        "google_fonts_url": "family=Playfair+Display:ital,wght@0,700;0,900;1,400&family=Bodoni+Moda:ital,wght@0,700;1,400&family=Lora:ital,wght@0,500;1,400&family=Inter:wght@400;600",
        "font_title": "'Playfair Display', 'Bodoni Moda', serif",
        "font_body": "'Lora', serif",
        "font_tag": "'Inter', sans-serif"
    },
    "infantojuvenil": {
        "google_fonts_url": "family=Outfit:wght@600;800&family=Philosopher:ital,wght@0,700;1,400&family=Quicksand:wght@500;700&family=Plus+Jakarta+Sans:wght@600;800",
        "font_title": "'Philosopher', 'Outfit', sans-serif",
        "font_body": "'Quicksand', sans-serif",
        "font_tag": "'Plus Jakarta Sans', sans-serif"
    },
    "academico_solene": {
        "google_fonts_url": "family=Cormorant+SC:wght@600;700&family=EB+Garamond:ital,wght@0,500;1,400&family=Source+Sans+3:wght@600;700",
        "font_title": "'Cormorant SC', serif",
        "font_body": "'EB Garamond', serif",
        "font_tag": "'Source Sans 3', sans-serif"
    },
    "misterio_thriller": {
        "google_fonts_url": "family=Syne:wght@700;800&family=Crimson+Text:ital,wght@0,600;1,400&family=Space+Mono:wght@700",
        "font_title": "'Syne', sans-serif",
        "font_body": "'Crimson Text', serif",
        "font_tag": "'Space Mono', monospace"
    },
    "poesia_contemporanea": {
        "google_fonts_url": "family=Italiana&family=Cormorant+Infant:ital,wght@0,600;1,400&family=Jost:wght@400;600",
        "font_title": "'Italiana', serif",
        "font_body": "'Cormorant Infant', serif",
        "font_tag": "'Jost', sans-serif"
    },
    "geek_scifi": {
        "google_fonts_url": "family=Orbitron:wght@700;900&family=Space+Grotesk:wght@500;700&family=Fira+Code:wght@600",
        "font_title": "'Orbitron', sans-serif",
        "font_body": "'Space Grotesk', sans-serif",
        "font_tag": "'Fira Code', monospace"
    }
}


# Heurística de sugestão de estilo_tipografico quando não informado explicitamente.
# Prioridade: overlay_estilo > framework > genero > default. Sempre sobrescrevível
# via config["estilo_tipografico"] — nenhuma destas linhas é uma verdade rígida.
OVERLAY_TO_ESTILO = {
    "overlay_gotouge_inherited_will": "imperial_oriental",
    "gotouge_inherited_will": "imperial_oriental",
    "overlay_tolkien": "imperial_oriental",
    "overlay_lewis": "academico_solene",
    "overlay_chesterton": "academico_solene",
    "overlay_rowling": "infantojuvenil",
}

FRAMEWORK_TO_ESTILO = {
    "brooks_story_engineering": "misterio_thriller",
    "snowflake": "imperial_oriental",
    "save_the_cat": "geek_scifi",
    "minto_pyramid": "academico_solene",
    "scholastic_aquinas": "academico_solene",
    "devotional_n_days": "poesia_contemporanea",
    "kishotenketsu": "infantojuvenil",
}

GENERO_TO_ESTILO = {
    "teologia": "academico_solene",
    "romance": "romance_classico",
    "ficcao": "misterio_thriller",
    "ficção": "misterio_thriller",
    "infantojuvenil": "infantojuvenil",
    "juvenil": "infantojuvenil",
    "poesia": "poesia_contemporanea",
    "suspense": "misterio_thriller",
    "misterio": "misterio_thriller",
    "mistério": "misterio_thriller",
    "thriller": "misterio_thriller",
    "ficcao_cientifica": "geek_scifi",
    "ficção_científica": "geek_scifi",
    "scifi": "geek_scifi",
}

DEFAULT_ESTILO_TIPOGRAFICO = "imperial_oriental"


def _hex_luminance(color: str) -> float:
    value = color.lstrip("#")
    if len(value) != 6:
        return 0.0
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def suggest_estilo_tipografico(config: Dict[str, Any]) -> str:
    """Sugere um estilo_tipografico quando config não define um explicitamente.
    Prioridade: overlay_estilo > framework > genero > default. O resultado é só
    uma sugestão de fallback — config["estilo_tipografico"] sempre tem prioridade
    (ver get_tokens)."""
    overlay = str(config.get("overlay_estilo", "")).strip().lower()
    if overlay in OVERLAY_TO_ESTILO:
        return OVERLAY_TO_ESTILO[overlay]

    framework = str(config.get("framework", "")).strip().lower()
    if framework in FRAMEWORK_TO_ESTILO:
        return FRAMEWORK_TO_ESTILO[framework]

    genero = str(config.get("genero", "")).strip().lower()
    if genero in GENERO_TO_ESTILO:
        return GENERO_TO_ESTILO[genero]

    return DEFAULT_ESTILO_TIPOGRAFICO


def get_tokens(config: Dict[str, Any]) -> Dict[str, Any]:
    from design_engine.color_strategy import build_color_plan

    theme = config.get("tema", "nanquim").lower()
    palette = COLOR_PALETTES.get(theme, COLOR_PALETTES["nanquim"]).copy()

    # Sobrescreve cor de capa personalizada se informada em HEX
    if config.get("cor_capa"):
        palette["bg_color"] = config["cor_capa"]
        # Uma cor customizada pode inverter a luminosidade da paleta original.
        # Mantém a cor de destaque, mas adapta os papéis semânticos de leitura.
        if _hex_luminance(str(config["cor_capa"])) < 0.18:
            palette["text_light"] = "#ffffff"
            palette["text_subtle"] = "#d1d5db"
            palette["soft_gold"] = "#f0e6d2"
            palette["box_bg"] = "rgba(255, 255, 255, 0.04)"

    requested_font_key = str(config.get("estilo_tipografico") or suggest_estilo_tipografico(config)).lower()
    font_key = requested_font_key if requested_font_key in FONT_THEMES else DEFAULT_ESTILO_TIPOGRAFICO
    font_theme = FONT_THEMES[font_key]
    color_plan = build_color_plan(config, palette)
    palette["bg_color"] = color_plan.dominant.color
    palette["secondary_color"] = color_plan.secondary.color
    palette["accent_color"] = color_plan.accent.color
    palette["gold_color"] = color_plan.accent.color

    return {
        "palette": palette,
        "fonts": font_theme,
        "estilo_tipografico": font_key,
        "color_plan": color_plan.to_dict(),
    }
