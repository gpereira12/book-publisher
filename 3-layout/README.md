<div align="center">

# 📐 Layout — Projeto 3 (Diagramação) & Motor Typst v4.0

**Hub Editorial Avançado e Pipeline de Diagramação: `Markdown AST → Typst / HTML → PDF / EPUB3`**

*Converte manuscritos em livros de alta qualidade gráfica com margens áureas, presets tipográficos, imagens emolduradas/sangradas e exportação híbrida.*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Typst](https://img.shields.io/badge/Typst-v0.11+-239DA8?style=flat-square&logo=typst&logoColor=white)](https://typst.app)
[![Playwright](https://img.shields.io/badge/Playwright-Headless_Chrome-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![EPUB3](https://img.shields.io/badge/EPUB-3.0-blue?style=flat-square)](https://w3.org/publishing/epub3)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## 🏛️ Visão Geral da Arquitetura (Hub Editorial)

O **Boutique de Livros** evoluiu para um **Hub Editorial Híbrido**, suportando dois motores de renderização de alta precisão: o tradicional pipeline web (`Markdown → HTML/Paged.js → Playwright`) e o novo motor ultra-rápido de diagramação nativa **Typst** (`Markdown AST → Typst Templates → PDF`).

```
                    ┌─────────────────────────┐
                    │ Manuscrito Original MD  │
                    │  + YAML Frontmatter     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │  Markdown AST Parser │
                     └───────────┬──────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
    ┌─────────────────────────┐     ┌─────────────────────────┐
    │    Typst Layout Engine  │     │   HTML5 / Paged.js Engine│
    │  (src/typst_exporter.py)│     │  (src/builder.py)       │
    └────────────┬────────────┘     └────────────┬────────────┘
                 │                               │
                 ▼                               ▼
     [ Typst Compile (CLI) ]         [ Playwright / Chromium ]
                 │                               │
                 ├───────────────────────────────┤
                 ▼                               ▼
        ┌─────────────────┐             ┌─────────────────┐
        │  PDF Impresso   │             │  PDF Digital /  │
        │  (Com Bleed 5mm)│             │     EPUB3       │
        └─────────────────┘             └─────────────────┘
```

---

## ✨ Funcionalidades Principais

| Categoria | Recursos e Detalhes |
|---|---|
| ⚡ **Motores de Renderização** | Typst (Ultra-rápido, tipografia perfeita) & HTML5 / Paged.js |
| 📐 **Formatos Editoriais** | A5, 14x21cm, Pocket (125x180mm), Trade (152x228mm) e A4 |
| 📏 **Proporção Áurea & Sangria** | Margens calculadas via Golden Ratio (1:1.618) + Bleed de 5mm para impressão offset |
| 🖼️ **Layout de Imagens** | Suporte a Molduras estilizadas, Imagens Sangradas (Full-Bleed 1 página) e Spread Duplo (2 páginas) |
| 🎨 **Elementos Gráficos** | Divisores decorativos SVG, capitulares, epígrafes e balões de mangá / quadrinhos |
| 📑 **Ficha Catalográfica & Folha de Rosto** | Geração dinâmica de CIP com contagem de páginas e metadados via YAML Frontmatter |
| 📖 **Exportação EPUB3** | Suporte planejado para publicação digital reflowable e e-readers |

---

## 📁 Estrutura do Projeto

```
3-layout/                      # Este módulo — invocado a partir da raiz do repositório
│
├── main.py                    # Orquestrador do módulo Layout e CLI interativo
├── README.md                  # Documentação da arquitetura e roadmap
│
└── src/
    ├── typst_exporter.py      # Compilador e integrador Typst (YAML Frontmatter + MD -> PDF)
    ├── parser.py              # Parser AST de Markdown e pré-processador de imagens
    ├── builder.py             # Builder de HTML5 e Paged.js
    ├── pdf_printer.py         # Renderizador Playwright (Chromium headless)
    │
    └── templates_typst/       # 🎨 Módulo de Layout & Templates Typst
        ├── book_base.typ      # Base engine: margens áureas, dimensões, folha de rosto e CIP
        ├── components.typ     # Molduras, full-bleed, double-spread, SVGs e balões de mangá
        └── romance.typ        # Preset clássico para literatura/romances

# na raiz do repositório:
├── requirements.txt           # Dependências Python (compartilhadas por todos os módulos)
├── inputs/                    # Manuscritos de entrada por livro
│   └── <nome_do_livro>/
│       ├── texto_original.md  # Manuscrito em Markdown
│       └── assets/            # Imagens, ilustrações, capas e figuras
│
└── outputs/                   # PDFs impressos (com sangria) e digitais gerados
```

---

## 🚀 Como Usar

*(comandos executados a partir da raiz do repositório)*

### Compilação via Typst Exporter (Novo Motor v4.0)

```bash
# Compilar um manuscrito com Frontmatter usando o preset Romance
python 3-layout/src/typst_exporter.py -i inputs/O_Olhar_Elevado/texto_original.md -o outputs/O_Olhar_Elevado/O_Olhar_Elevado_Typst.pdf --preset romance
```

### Compilação via Pipeline Tradicional (HTML / Paged.js)

```bash
python 3-layout/main.py --book-dir O_Olhar_Elevado --format A5 --theme Creme
```

---

## 🛤️ Roadmap v4.0 — Hub Editorial & Motor Typst

> *Planejamento estratégico de evolução da plataforma de diagramação automatizada.*

- [x] **v4.0.0 — Arquitetura de Templates Typst Base**
  - [x] Criação do `src/templates_typst/book_base.typ` com Proporção Áurea e Ficha Catalográfica dinâmica.
  - [x] Criação do `src/templates_typst/components.typ` (`#moldura()`, `#full-bleed()`, `#double-spread()`, `#svg-divider()`, balões de mangá).
  - [x] Preset tipográfico `src/templates_typst/romance.typ` para literatura.
  - [x] Script compilador `src/typst_exporter.py` com suporte a YAML Frontmatter.
- [ ] **v4.1.0 — Suporte Total a EPUB3 e AST Markdown Extensível**
  - [ ] Parser de AST em Python integrando `marko` ou `mistune` para representação intermediária única.
  - [ ] Gerador nativo de `.epub` 3.0 com suporte a CSS Reflowable e metadados Dublin Core.
- [ ] **v4.2.0 — Presets de Mangás e HQs**
  - [ ] Template Typst dedicado para leitura Right-to-Left (RTL), grids de painéis e onomatopeias em camadas SVG.
- [ ] **v4.3.0 — Interface Web & Preview em Tempo Real**
  - [ ] Dashboard Web em FastAPI + WebAssembly/Typst para visualização síncrona da diagramação.

---

## 📜 Licença

Distribuído sob a licença **MIT**. Veja `LICENSE` para mais detalhes.
