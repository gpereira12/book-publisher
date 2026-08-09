<div align="center">

# 📚 Hub Editorial — Boutique de Livros

**Pipeline industrial de publicação: `Ideia/Briefing → Manuscrito → Revisão → Diagramação → Capa → Aprovação Final`**

*Transforma Markdown/YAML em livros comerciais prontos para gráfica (PDF/X 300 DPI, EAN-13, CMYK) e e-books digitais (EPUB3).*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Typst](https://img.shields.io/badge/Typst-v0.11+-239DA8?style=flat-square&logo=typst&logoColor=white)](https://typst.app)
[![Playwright](https://img.shields.io/badge/Playwright-Headless_Chrome-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![EPUB3](https://img.shields.io/badge/EPUB-3.0-blue?style=flat-square)](https://w3.org/publishing/epub3)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## 🏛️ Os 5 Módulos do Hub

Cada módulo é um projeto independente (pasta numerada + `main.py` próprio), encadeado em pipeline. O número identifica a ordem no pipeline; o codinome é como nos referimos a cada motor no dia a dia.

| # | Codinome | Pasta | Função |
|---|---|---|---|
| 1 | **Draft** | [`1-draft/`](1-draft/README.md) | Escrita — gera o manuscrito a partir de briefing/framework narrativo |
| 2 | **Edit** | [`2-edit/`](2-edit/README.md) | Revisão editorial em 5 camadas (Dreyer & King, regência, verba dicendi, style sheet, legibilidade) |
| 3 | **Layout** | [`3-layout/README.md`](3-layout/README.md) | Diagramação dual-engine (Typst + Paged.js) → PDF de impressão + EPUB3 |
| 4 | **Cover** | [`4-cover/`](4-cover/README.md) | Capas & artes — motor híbrido HTML/Playwright + presets Typst, EAN-13, selos editoriais |
| 5 | **Ship** | [`5-ship/`](5-ship/) | QA pré-impressão (PDF/X, CMYK, 300 DPI, EPUBCheck) + empacotamento final — **em construção** |

Status: Draft, Edit, Layout e Cover estão completos e em uso; Ship é o próximo passo.

---

## 📁 Estrutura do Repositório

```
Livros/
│
├── 1-draft/            # Projeto 1 — Escrita (frameworks narrativos, dossiês de personagem)
├── 2-edit/              # Projeto 2 — Revisão (5 camadas de qualidade editorial)
├── 3-layout/            # Projeto 3 — Diagramação (Typst / Paged.js → PDF + EPUB3)
├── 4-cover/             # Projeto 4 — Capas & Artes (HTML+Playwright / Typst, EAN-13, selos)
├── 5-ship/              # Projeto 5 — QA Pre-Flight & empacotamento (a iniciar)
│
├── inputs/              # Manuscritos e assets de entrada, por livro
│   └── <nome_do_livro>/
├── outputs/              # PDFs, EPUBs, capas e relatórios gerados, por livro
│   └── <nome_do_livro>/{pdf,epub,capas,relatorios}/
│
├── resources/logos/      # Selos editoriais (coala, cia-de-jesus, eldoria, ilios)
├── branding_system/      # Templates de prompt para arte/ilustração de capa
└── requirements.txt       # Dependências Python compartilhadas
```

---

## 🚀 Uso Rápido

*(comandos executados a partir da raiz do repositório)*

```bash
# 1. Escrita — gera o manuscrito
python 1-draft/main.py --book-dir meu_livro

# 2. Revisão — audita e lapidação editorial (dispara o Layout automaticamente com --auto-approve)
python 2-edit/main.py --book-dir meu_livro --auto-approve

# 3. Diagramação — PDF de impressão + digital + EPUB3
python 3-layout/main.py --book-dir meu_livro --format A5 --theme Creme

# 4. Capa — motor híbrido (auto-roteia HTML ou Typst conforme book_config.yaml)
python 4-cover/main.py --book-dir meu_livro
```

---

## 📜 Licença

Distribuído sob a licença **MIT**. Veja `LICENSE` para mais detalhes.
