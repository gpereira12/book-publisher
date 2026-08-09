# 🎨 Cover — Projeto 4 (Capas & Artes): Cover & Asset Generation Engine

Este projeto é o motor de geração de capas gráficas e artes do **Hub Editorial**. Ele lê o número exato de páginas gerado pelo **Layout (Projeto 3 — Diagramação)** e constrói a **Capa Horizontal Aberta Completa** para gráfica em PDF (CMYK / 300 DPI).

---

## 🏛️ Funcionalidades

1. **Cálculo Matemático da Lombada (`spine_calculator.py`)**: Calcula a espessura da lombada baseando-se na contagem real de páginas do PDF e no tipo de papel.
2. **Suporte a Brochura & Capa Dura**:
   - *Brochura:* Inclui Orelhas de 70mm e sangria de 10mm.
   - *Capa Dura:* Inclui Vira de 35mm e Calhas de 10mm.
3. **Motor Duplo (`design_engine/`)** — `main.py` roteia automaticamente entre os dois motores conforme `book_config.yaml`:
   - **Motor A — HTML5/CSS3 + Playwright** (`engine_html.py`): capas ilustradas/full-bleed com imagem, em 3 padrões de composição (`layout_patterns/`: Full-Bleed, Split/Tarja, Moldura/Medalhão).
   - **Motor B — Typst** (`engine_typst.py`): presets minimalistas/tipográficos sem imagem, gerados via Typst compilado em `outputs/<livro>/capas/capa_horizontal_grafica.pdf`.
   - Geometria (`geometry_engine.py`) e paletas/fontes por gênero (`design_tokens.py`) são compartilhadas pelos dois motores.
4. **Código de Barras EAN-13 (`barcode_generator.py`)**: gerador de vetor SVG hand-rolled a partir do ISBN, usado por ambos os motores.

> `4-cover/templates_typst/cover_base.typ` é um protótipo de terceiro motor (capa Typst com imagem full-bleed real) que ficou órfão — não é chamado por nenhum código ativo. Mantido apenas como referência para uma futura variante "Typst ilustrado".

---

## 🚀 Como Executar

```bash
python 4-cover/main.py --book-dir cronicas_chinesas_para_pequenos_guerreiros
```
