"""
4-cover/design_engine/compositor.py
--------------------------------------
Compositing de capa: fundo texturizado + ilustração + degradê (Frente 2 do
Cover v2). Processamento de imagem puro (Pillow), sem geração por IA.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PIL import Image, ImageOps


def load_texture(estilo_key: str, textures_dir: Path = Path("resources/textures")) -> Image.Image:
    """Carrega resources/textures/<estilo_key>.jpg. A biblioteca de texturas
    reais é fornecida externamente (ver resources/textures/README.md) — não há
    nenhuma textura embutida neste repositório."""
    texture_file = textures_dir / f"{estilo_key}.jpg"
    if not texture_file.exists():
        raise FileNotFoundError(
            f"Textura não encontrada: {texture_file}. Adicione um arquivo JPG em "
            f"'{textures_dir}/{estilo_key}.jpg' para habilitar composicao_capa "
            f"para o estilo '{estilo_key}' (ver {textures_dir}/README.md)."
        )
    return Image.open(texture_file).convert("RGB")


def composite_cover_art(
    texture_img: Image.Image,
    illustration_img: Image.Image,
    *,
    fade_direction: str = "bottom",
    fade_start: float = 0.5,
    output_size_px: Optional[Tuple[int, int]] = None,
    target_aspect_ratio: Optional[float] = None,
    focus: Tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    """Compõe a ilustração sobre a textura com um degradê de transparência,
    via Image.linear_gradient/radial_gradient + Image.composite (Pillow puro)."""
    if not 0 <= fade_start <= 1:
        raise ValueError("fade_start deve estar entre 0 e 1")
    if not all(0 <= value <= 1 for value in focus):
        raise ValueError("focus deve conter valores entre 0 e 1")

    if output_size_px:
        size = output_size_px
    elif target_aspect_ratio:
        source_w, source_h = illustration_img.size
        source_ratio = source_w / source_h
        if source_ratio > target_aspect_ratio:
            size = (max(1, round(source_h * target_aspect_ratio)), source_h)
        else:
            size = (source_w, max(1, round(source_w / target_aspect_ratio)))
    else:
        size = illustration_img.size

    resampling = Image.Resampling.LANCZOS
    texture = ImageOps.fit(texture_img.convert("RGB"), size, method=resampling, centering=focus)
    illustration = ImageOps.fit(illustration_img.convert("RGB"), size, method=resampling, centering=focus)

    w, h = size
    mask = Image.new("L", size, 255)  # 255 = ilustração opaca; 0 = textura pura
    gradient = Image.linear_gradient("L")  # 256x256, 0 no topo -> 255 na base
    fade_start_px = int(h * fade_start)

    if fade_direction == "bottom":
        band_h = max(1, h - fade_start_px)
        band = gradient.resize((w, band_h)).transpose(Image.FLIP_TOP_BOTTOM)
        mask.paste(band, (0, fade_start_px))
    elif fade_direction == "top":
        band_h = max(1, fade_start_px)
        band = gradient.resize((w, band_h))
        mask.paste(band, (0, 0))
    elif fade_direction == "radial":
        radial = Image.radial_gradient("L").resize(size)
        mask = radial.point(lambda p: 255 - p)
    else:
        raise ValueError(f"fade_direction inválido: {fade_direction!r} (use 'top', 'bottom' ou 'radial')")

    return Image.composite(illustration, texture, mask)


def build_cover_art(config: Dict[str, Any], book_dir: Path) -> Path:
    """Resolve estilo -> textura, lê a ilustração bruta, compõe e grava em
    assets/capa.jpg. Chamado por main.py apenas quando composicao_capa=true."""
    from design_engine.cover_spec import build_cover_spec
    from design_engine.design_tokens import get_tokens

    tokens = get_tokens(config)
    estilo_key = config.get("textura_fundo") or tokens["estilo_tipografico"]

    assets_dir = book_dir / "assets"
    illustration_rel = config.get("ilustracao_bruta", "assets/illustration_raw.png")
    illustration_file = Path(illustration_rel)
    if not illustration_file.is_absolute():
        illustration_file = book_dir / illustration_rel
    if not illustration_file.exists():
        alt = illustration_file.with_suffix(".jpg")
        if alt.exists():
            illustration_file = alt
    if not illustration_file.exists():
        raise FileNotFoundError(
            f"Ilustração bruta não encontrada: {illustration_file}. Configure "
            f"'ilustracao_bruta' em book_config.yaml ou coloque o arquivo em "
            f"assets/illustration_raw.png."
        )

    texture_img = load_texture(estilo_key)
    illustration_img = Image.open(illustration_file)

    fade_direction = config.get("fade_direction", "bottom")
    spec = build_cover_spec(config, 0.0)
    target_ratio = (spec.page_w_mm + spec.bleed_mm) / spec.total_h_mm
    focus = (float(config.get("foco_x", 0.5)), float(config.get("foco_y", 0.5)))
    composed = composite_cover_art(
        texture_img,
        illustration_img,
        fade_direction=fade_direction,
        fade_start=float(config.get("fade_start", 0.5)),
        target_aspect_ratio=target_ratio,
        focus=focus,
    )

    assets_dir.mkdir(parents=True, exist_ok=True)
    out_file = assets_dir / "capa.jpg"
    composed.save(out_file, format="JPEG", quality=92)
    print(
        f"🖼️  [Cover] Compositing aplicado (textura '{estilo_key}' + ilustração + "
        f"degradê '{fade_direction}', foco {focus}) -> {out_file}"
    )
    return out_file
