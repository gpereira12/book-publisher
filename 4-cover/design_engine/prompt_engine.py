"""
4-cover/design_engine/prompt_engine.py
----------------------------------------
Motor de Prompt de Capa: vocabulário de fotografia/cinema (plano, ângulo,
iluminação, composição) combinado com o estilo visual por gênero editorial.
Produz um prompt em texto puro (provider-agnostic) — o formato específico de
uma ferramenta (ex: flags do Midjourney) é aplicado só em format_for_tool().
"""

from pathlib import Path
from fractions import Fraction
from typing import Dict, Any, List, Optional

SHOT_TYPES: Dict[str, str] = {
    "close_up": "close-up shot, tight framing on the subject's most meaningful detail",
    "medium": "medium shot, subject framed from the waist up, balanced context and detail",
    "wide": "wide establishing shot, subject small within a full environment",
}

CAMERA_ANGLES: Dict[str, str] = {
    "eye_level": "eye-level camera angle, neutral and grounded perspective",
    "low_angle": "low-angle shot looking up at the subject, heroic and imposing",
    "high_angle": "high-angle shot looking down at the subject, vulnerable or diminutive",
    "dutch": "dutch tilt angle, slightly rotated frame, quiet tension",
}

LIGHTING_SCHEMES: Dict[str, str] = {
    "rembrandt": "Rembrandt lighting, single key light at 45 degrees, small triangle of light on the shadowed cheek",
    "chiaroscuro": "chiaroscuro lighting, extreme contrast between deep shadow and bright highlight",
    "backlight": "backlight / rim lighting, subject silhouetted with a glowing edge",
    "golden_hour": "golden hour lighting, warm low-angle sunlight, long soft shadows",
}

COMPOSITION_RULES: Dict[str, str] = {
    "rule_of_thirds": "composed on the rule of thirds, subject off-center",
    "negative_space_top": "generous negative space in the upper third of the frame",
    "centered_symmetry": "centered, symmetrical composition",
}

# Estilo visual por gênero — mesmas 7 chaves canônicas de design_tokens.FONT_THEMES
GENRE_VISUAL_STYLES: Dict[str, Dict[str, Any]] = {
    "imperial_oriental": {
        "style": "cinematic photorealistic illustration with oriental ink-wash (shuimo) influence",
        "mood_keywords": ["ornate", "imperial", "epic", "ancient China", "gold accents"],
        "default_lighting": "golden_hour",
    },
    "romance_classico": {
        "style": "classic oil painting illustration, romantic realism",
        "mood_keywords": ["elegant", "warm", "intimate", "timeless"],
        "default_lighting": "rembrandt",
    },
    "infantojuvenil": {
        "style": "flat vector illustration, children's book style",
        "mood_keywords": ["playful", "friendly", "bright colors", "rounded shapes"],
        "default_lighting": "golden_hour",
    },
    "academico_solene": {
        "style": "engraved etching illustration, classical academic style",
        "mood_keywords": ["solemn", "scholarly", "muted tones", "formal"],
        "default_lighting": "rembrandt",
    },
    "misterio_thriller": {
        "style": "high-contrast cinematic photography, noir influence",
        "mood_keywords": ["tense", "shadowy", "urban", "moody"],
        "default_lighting": "chiaroscuro",
    },
    "poesia_contemporanea": {
        "style": "minimalist watercolor illustration",
        "mood_keywords": ["delicate", "quiet", "abstract", "airy"],
        "default_lighting": "backlight",
    },
    "geek_scifi": {
        "style": "digital concept art, science-fiction illustration",
        "mood_keywords": ["futuristic", "neon accents", "technological", "sleek"],
        "default_lighting": "backlight",
    },
}

DEFAULT_ESTILO_KEY = "imperial_oriental"
DEFAULT_ASPECT_RATIO = "2:3"


def build_cover_prompt(
    subject: str,
    estilo_key: str,
    *,
    shot_type: str = "medium",
    camera_angle: str = "eye_level",
    lighting: Optional[str] = None,
    composition: str = "rule_of_thirds",
    negative_space_for_title: bool = True,
    extra_keywords: Optional[List[str]] = None,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    exclude_text: bool = True,
    style_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Monta um prompt de capa a partir do assunto (subject) + vocabulário
    técnico de fotografia/cinema + estilo visual do gênero. Retorna texto puro
    (sem flags de ferramenta) e os campos resolvidos, para uso programático."""
    genre = GENRE_VISUAL_STYLES.get(estilo_key, GENRE_VISUAL_STYLES[DEFAULT_ESTILO_KEY])
    lighting_key = lighting or genre["default_lighting"]

    shot_phrase = SHOT_TYPES.get(shot_type, SHOT_TYPES["medium"])
    angle_phrase = CAMERA_ANGLES.get(camera_angle, CAMERA_ANGLES["eye_level"])
    lighting_phrase = LIGHTING_SCHEMES.get(lighting_key, LIGHTING_SCHEMES["rembrandt"])
    composition_phrase = COMPOSITION_RULES.get(composition, COMPOSITION_RULES["rule_of_thirds"])

    parts = [
        subject.strip().rstrip("."),
        style_override or genre["style"],
        ", ".join(genre["mood_keywords"]),
        shot_phrase,
        angle_phrase,
        lighting_phrase,
        composition_phrase,
    ]
    if negative_space_for_title and composition != "negative_space_top":
        parts.append(COMPOSITION_RULES["negative_space_top"])
    if extra_keywords:
        parts.append(", ".join(extra_keywords))
    if exclude_text:
        parts.append("cover artwork only, no typography, no letters, no words, no logos, no watermark")

    prompt = ". ".join(p for p in parts if p) + "."

    return {
        "prompt": prompt,
        "structured": {
            "subject": subject,
            "estilo_key": estilo_key,
            "shot_type": shot_type,
            "camera_angle": camera_angle,
            "lighting": lighting_key,
            "composition": composition,
            "negative_space_for_title": negative_space_for_title,
            "extra_keywords": extra_keywords or [],
            "exclude_text": exclude_text,
            "style_override": style_override,
        },
        "provider_hints": {
            "aspect_ratio": aspect_ratio,
            "negative_prompt": "text, letters, words, logo, watermark, signature" if exclude_text else "photographic background, human figures",
        },
    }


def format_for_tool(prompt_data: Dict[str, Any], tool: str = "plain") -> str:
    """tool='plain' (default): texto puro, pronto para uma API de imagem.
    tool='midjourney': anexa as flags --ar/--v que a ferramenta espera."""
    prompt = prompt_data["prompt"]
    if tool == "midjourney":
        ar = prompt_data.get("provider_hints", {}).get("aspect_ratio", DEFAULT_ASPECT_RATIO)
        return f"{prompt} --ar {ar} --v 6.0"
    return prompt


def generate_cover_prompt_set(config: Dict[str, Any], briefs: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Generaliza o antigo loop ad-hoc de branding_system/generate_prompts.py:
    aplica build_cover_prompt a uma lista de briefs (ou a um brief genérico
    derivado do book_config, se nenhum for informado)."""
    from design_engine.cover_spec import build_cover_spec
    from design_engine.design_tokens import get_tokens, suggest_estilo_tipografico

    estilo_key = config.get("estilo_visual") or config.get("estilo_tipografico") or suggest_estilo_tipografico(config)
    spec = build_cover_spec(config, 0.0)
    ratio = Fraction(round(spec.page_w_mm + spec.bleed_mm), round(spec.total_h_mm)).limit_denominator(50)
    aspect_ratio = f"{ratio.numerator}:{ratio.denominator}"
    color_plan = get_tokens(config)["color_plan"]
    color_keywords = [
        f"dominant color {color_plan['dominant']['color']} approximately 70 percent",
        f"secondary color {color_plan['secondary']['color']} approximately 20 percent",
        f"accent color {color_plan['accent']['color']} approximately 10 percent",
    ]

    if not briefs:
        titulo = config.get("titulo", "book cover subject")
        sinopse = config.get("sinopse", "")
        subject = f"{titulo}: {sinopse}" if sinopse else titulo
        if config.get("gerar_direcoes_visuais"):
            briefs = [
                {"label": "direcao_figurativa", "subject": subject, "extra_keywords": ["character-led narrative scene"]},
                {"label": "direcao_simbolica", "subject": subject, "shot_type": "close_up", "extra_keywords": ["single symbolic object, visual metaphor"]},
                {
                    "label": "direcao_grafica",
                    "subject": subject,
                    "composition": "centered_symmetry",
                    "style_override": "graphic editorial illustration with restrained ink-wash shapes",
                    "extra_keywords": ["flat layered composition, symbolic geometry, restrained palette"],
                },
            ]
        else:
            briefs = [{"label": "capa_principal", "subject": subject}]

    results = []
    for brief in briefs:
        extras = brief.get("extra_keywords") or config.get("estilo_visual_extra") or []
        if isinstance(extras, str):
            extras = [extras]
        prompt_data = build_cover_prompt(
            subject=brief.get("subject", config.get("titulo", "book cover subject")),
            estilo_key=brief.get("estilo_key", estilo_key),
            shot_type=brief.get("shot_type", "medium"),
            camera_angle=brief.get("camera_angle", "eye_level"),
            lighting=brief.get("lighting"),
            composition=brief.get("composition", "rule_of_thirds"),
            negative_space_for_title=brief.get("negative_space_for_title", True),
            extra_keywords=list(extras) + color_keywords,
            aspect_ratio=brief.get("aspect_ratio", aspect_ratio),
            exclude_text=brief.get("exclude_text", True),
            style_override=brief.get("style_override"),
        )
        prompt_data["label"] = brief.get("label", "capa")
        results.append(prompt_data)
    return results


def save_prompt_set(prompts: List[Dict[str, Any]], book_dir: Path) -> Path:
    """Grava cada prompt em assets/prompts/<label>.json (dados estruturados)
    e assets/prompts/<label>.txt (texto puro, pronto pra copiar/colar)."""
    import json

    prompts_dir = book_dir / "assets" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    for prompt_data in prompts:
        label = prompt_data.get("label", "capa")
        (prompts_dir / f"{label}.json").write_text(
            json.dumps(prompt_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (prompts_dir / f"{label}.txt").write_text(prompt_data["prompt"], encoding="utf-8")

    return prompts_dir
