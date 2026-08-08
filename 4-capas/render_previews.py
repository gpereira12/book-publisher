#!/usr/bin/env python3
"""
4-capas/render_previews.py
--------------------------
Gera arquivos PNG para a Opção A (HTML5/CSS3) e Opção C (SVG Composite).
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

def render_previews():
    book_dir = Path("inputs") / "cronicas_chinesas_para_pequenos_guerreiros"
    out_dir = Path("outputs") / "cronicas_chinesas_para_pequenos_guerreiros" / "capas"
    
    files = {
        "Opção A (HTML5/CSS3)": (book_dir / "capa_opcao_a.html", out_dir / "capa_opcao_a_preview.png"),
        "Opção C (SVG Composite)": (book_dir / "capa_opcao_c_wrapper.html", out_dir / "capa_opcao_c_preview.png"),
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, (src_file, dst_png) in files.items():
            if src_file.exists():
                page = browser.new_page(viewport={"width": 1600, "height": 1172})
                page.goto(src_file.resolve().as_uri())
                page.screenshot(path=str(dst_png), full_page=True)
                print(f"📸 Preview de [{name}] gerado em: {dst_png}")
        browser.close()

if __name__ == "__main__":
    render_previews()
