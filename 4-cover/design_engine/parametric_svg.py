"""Primitivas paramétricas para ornamentos SVG complexos e determinísticos."""

from __future__ import annotations

import math


def radial_repeat(fragment: str, count: int, cx: float, cy: float) -> str:
    count = max(1, count)
    items = [f'<g transform="rotate({360 * index / count:.3f} {cx} {cy})">{fragment}</g>' for index in range(count)]
    return "".join(items)


def linear_repeat(fragment: str, count: int, start_x: float, step_x: float) -> str:
    return "".join(f'<g transform="translate({start_x + index * step_x:.3f} 0)">{fragment}</g>' for index in range(max(1, count)))


def render_rosette_fragment(color: str, size: float, complexity: int = 3) -> str:
    complexity = max(1, min(5, complexity))
    center = size / 2
    petals = 4 + complexity * 2
    petal_length = size * 0.31
    petal_width = size * (0.055 + complexity * 0.006)
    fragment = (
        f'<path d="M {center},{center - size*0.08} '
        f'C {center-petal_width},{center-petal_length*0.55} {center-petal_width},{center-petal_length} {center},{center-petal_length} '
        f'C {center+petal_width},{center-petal_length} {center+petal_width},{center-petal_length*0.55} {center},{center-size*0.08} Z"/>'
    )
    rings = "".join(
        f'<circle cx="{center}" cy="{center}" r="{size*(0.12 + layer*0.055):.3f}" fill="none" stroke="{color}" stroke-width="{size*0.008:.3f}" opacity="{0.8-layer*0.1:.2f}"/>'
        for layer in range(max(0, complexity - 2))
    )
    return (
        f'<g fill="none" stroke="{color}" stroke-width="{size*0.012:.3f}" stroke-linejoin="round">'
        f'{radial_repeat(fragment, petals, center, center)}{rings}</g>'
        f'<circle cx="{center}" cy="{center}" r="{size*0.045}" fill="{color}"/>'
    )


def render_meander_fragment(color: str, width: float, height: float, complexity: int = 3) -> str:
    """Faixa de chave geométrica repetível, com uma ou mais linhas de detalhe."""
    complexity = max(1, min(5, complexity))
    unit = height * 1.7
    count = max(2, math.ceil(width / unit))
    motif = (
        f'<path d="M 0,{height*0.72} H {unit*0.7} V {height*0.28} H {unit*0.25} '
        f'V {height*0.55} H {unit*0.52}" fill="none" stroke="{color}" '
        f'stroke-width="{height*0.09}" stroke-linecap="square" stroke-linejoin="miter"/>'
    )
    details = ""
    if complexity >= 3:
        details += f'<line x1="0" y1="{height*0.12}" x2="{width}" y2="{height*0.12}" stroke="{color}" stroke-width="{height*0.035}" opacity="0.65"/>'
    if complexity >= 4:
        details += f'<line x1="0" y1="{height*0.88}" x2="{width}" y2="{height*0.88}" stroke="{color}" stroke-width="{height*0.035}" opacity="0.65"/>'
    return f'<g>{linear_repeat(motif, count, 0, unit)}{details}</g>'


def render_complex_band(color: str, width: int = 360, height: int = 22, complexity: int = 3) -> str:
    fragment = render_meander_fragment(color, width, height, complexity)
    return f'''<svg class="ornament-band" viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs><clipPath id="band-clip"><rect width="{width}" height="{height}"/></clipPath></defs>
  <g clip-path="url(#band-clip)">{fragment}</g>
</svg>'''


def render_complex_rosette(color: str, size: int = 160, complexity: int = 3) -> str:
    return f'''<svg class="ornament-rosette" viewBox="0 0 {size} {size}" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
  {render_rosette_fragment(color, size, complexity)}
</svg>'''
