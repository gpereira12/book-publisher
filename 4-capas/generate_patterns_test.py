#!/usr/bin/env python3
"""
4-capas/generate_patterns_test.py
---------------------------------
Gera e renderiza os previews em alta definição dos Padrões 1, 2 e 3 para o livro Crônicas Chinesas.
"""

import sys
from pathlib import Path
import yaml
from playwright.sync_api import sync_playwright

sys.path.append(str(Path(__file__).parent))
from design_engine.engine_html import render_html_cover

def generate_all_patterns():
    book_dir = Path("inputs") / "cronicas_chinesas_para_pequenos_guerreiros"
    config = yaml.safe_load((book_dir / "book_config.yaml").read_text(encoding="utf-8"))
    out_dir = Path("outputs") / "cronicas_chinesas_para_pequenos_guerreiros" / "capas"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("🎨 Gerando os 3 Padrões de Composição (Padrão 1, Padrão 2 e Padrão 3)...")

    # 1. Renderiza os PDFs individualmente
    for pat_id in [1, 2, 3]:
        pdf_path = render_html_cover(config, 3.0, book_dir, pattern_id=pat_id)

    # 2. Captura Screenshots PNG
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for pat_id in [1, 2, 3]:
            html_file = book_dir / f"capa_padrao_{pat_id}.html"
            dst_png = out_dir / f"preview_padrao_{pat_id}.png"

            page = browser.new_page(viewport={"width": 1600, "height": 1172})
            page.goto(html_file.resolve().as_uri())
            page.screenshot(path=str(dst_png), full_page=True)
            print(f"📸 Preview do Padrão {pat_id} gerado em: {dst_png}")

        browser.close()

if __name__ == "__main__":
    generate_all_patterns()
