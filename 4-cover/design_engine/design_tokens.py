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


def get_tokens(config: Dict[str, Any]) -> Dict[str, Any]:
    theme = config.get("tema", "nanquim").lower()
    palette = COLOR_PALETTES.get(theme, COLOR_PALETTES["nanquim"]).copy()
    
    # Sobrescreve cor de capa personalizada se informada em HEX
    if config.get("cor_capa"):
        palette["bg_color"] = config["cor_capa"]
        
    font_key = config.get("estilo_tipografico", "imperial_oriental").lower()
    font_theme = FONT_THEMES.get(font_key, FONT_THEMES["imperial_oriental"])
    
    return {
        "palette": palette,
        "fonts": font_theme
    }
