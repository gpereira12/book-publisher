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
| 🖼️ **Layout de Imagens** | Molduras, imagens sangradas, spread duplo e abertura ilustrada com título, trecho editável e degradê gerado pelo layout |
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
        ├── components.typ     # Molduras, full-bleed, spreads, abertura ilustrada, SVGs e balões
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

### Abertura de capítulo ilustrada

O componente `illustrated-chapter-opener` cria uma abertura em página ímpar com
título, rótulo, atribuição opcional, trecho inicial e imagem inferior. O texto
continua editável e o degradê é aplicado pela diagramação, preservando o arquivo
de arte original. Altura da imagem, altura do degradê, formato e cores são
parâmetros, portanto o componente pode ser reutilizado em livros e proporções
diferentes.

```typst
#illustrated-chapter-opener(
  title: [Título do capítulo],
  chapter-label: [Conto 1],
  attribution: [Origem ou crédito opcional],
  opening-text: [Trecho inicial do capítulo.],
  image-path: "assets/interior/c01_s01_abertura.png",
  page-width: 125mm,
  page-height: 180mm,
)
```

### Prova de conto totalmente ilustrado

O modo `--illustrated-chapters` é o orquestrador de livros ilustrados. Ele lê o
manuscrito revisado e o `plano_ilustracoes.yaml`, aceita somente artes aprovadas
para layout e monta, para cada conto, a sequência editorial declarada no plano:
abertura em página ímpar, três ou mais spreads com texto integrado e página final
de reflexão. Três spreads são o piso do preset, não um total universal.
Também incorpora sangria, `TrimBox`, folios e visualização PDF em `TwoPageRight`.

A cor do papel não é universal: ela parte do campo `theme` do front matter de
cada obra (`Creme` ou `Branco`). Uma obra pode sobrescrever as cores do tema com
`layout_palette` (`paper`, `ink`, `accent` e `muted`, em hexadecimal). Nas
aberturas, o campo claro acompanha a altura real do título, crédito e introdução,
e só então se dissolve na ilustração. Os fólios recebem um medalhão discreto para
continuarem legíveis sobre fundos claros ou escuros.

O marcador de abertura usa `CONTO` em versalete espaçada e um pequeno selo na cor
de destaque contendo o número. A referência visual chinesa vem da geometria do
selo, sem recorrer a uma imitação caligráfica. Os títulos permanecem na família
editorial de alta legibilidade.

Nas páginas de reflexão, a virtude deve ser declarada em `book_config.yaml` por
meio de `virtude_tomista`, `ideograma_virtude` e `leitura_ideograma`. O motor usa
esses dados para desenhar uma assinatura vetorial discreta, formada pelo termo
chinês, sua leitura e a virtude em português. O elemento não é inferido nem usado
como ornamento genérico: a correspondência conceitual precisa ser validada antes
da exportação.

```bash
python 3-layout/main.py \
  --book-dir cronicas_chinesas_para_pequenos_guerreiros \
  --illustrated-chapters 1,2 \
  --output outputs/cronicas_chinesas_para_pequenos_guerreiros/pdf/prova_ilustrada_contos_01_02.pdf
```

Essa saída é uma **prova editorial**, portanto deve ser conferida em visão de
duas páginas antes da aprovação. A distribuição automática preserva parágrafos
e trata a medianiz como zona proibida, mas contraste, recorte, ritmo narrativo e
posição dos blocos continuam sujeitos à validação humana.

No modo adaptativo, a quantidade de spreads vem de cada capítulo do
`plano_ilustracoes.yaml`. O motor não comprime um capítulo longo para caber em
três spreads nem cria páginas sem aviso: a revisão recomenda a ampliação com base
na densidade do Conto 1 e o editor aprova o novo mapa antes da geração das artes.

O compositor de texto das páginas ilustradas não usa uma caixa fixa. Ele mede a
altura real do conteúdo, compara a complexidade visual das faixas superior e
inferior, penaliza regiões com rostos detectados e escolhe a zona menos intrusiva.
Os véus usam máscara alfa contínua, com bordas esmaecidas e transição suave para
a ilustração, sem faixas vetoriais visíveis. A mancha textual mantém uma área de
respiro interna antes do início do esmaecimento. Quando o conteúdo é longo, o motor
pode dividi-lo em dois véus de leitura - um no alto e
outro embaixo - sempre entre parágrafos. O corpo nominal é 9,6 pt nas páginas
ilustradas, 9,35 pt na abertura e 10 pt na reflexão; a redução automática das
páginas ilustradas é limitada a 8,85 pt.

Quando a conferência visual detectar disputa com um rosto ou outro elemento
narrativo, a cena pode registrar `distribuicao_texto_paginas`, com uma decisão
para cada metade do spread: `auto`, `top`, `bottom` ou `split`. O modo `split`
divide o conteúdo somente entre parágrafos e distribui os blocos no topo e no
rodapé. Como se trata de uma intervenção editorial, o motor deve avisar antes de
consolidá-la no plano de ilustrações.

### Contrato de entrada das imagens

O Layout não deve receber diretamente uma imagem recém-gerada. O projeto
[`5-illustration`](../5-illustration/README.md) confere dimensões com sangria,
resolução efetiva, perfil ICC, formato e medianiz antes da composição. Ele avisa
primeiro e só corrige mediante confirmação explícita. Revisão artística e comparação
semântica com o manuscrito permanecem portões editoriais; somente ativos marcados
como `aprovada_para_layout` devem entrar na composição.

Depois de aplicar título e texto, o Layout ainda deverá produzir uma prova para a
revisão conjunta da página. Essa etapa verifica legibilidade, contraste, recorte,
sangria, medianiz, zonas seguras e coerência final entre texto e imagem. Assim, a
aprovação da arte isolada não substitui a aprovação da página diagramada.

---

## 🛤️ Roadmap v4.0 — Hub Editorial & Motor Typst

> *Planejamento estratégico de evolução da plataforma de diagramação automatizada.*

- [x] **v4.0.0 — Arquitetura de Templates Typst Base**
  - [x] Criação do `src/templates_typst/book_base.typ` com Proporção Áurea e Ficha Catalográfica dinâmica.
  - [x] Criação do `src/templates_typst/components.typ` (`#moldura()`, `#full-bleed()`, `#double-spread()`, `#illustrated-chapter-opener()`, `#svg-divider()`, balões de mangá).
  - [x] Preset tipográfico `src/templates_typst/romance.typ` para literatura.
  - [x] Script compilador `src/typst_exporter.py` com suporte a YAML Frontmatter.
- [ ] **v4.1.0 — Suporte Total a EPUB3 e AST Markdown Extensível**
  - [ ] Parser de AST em Python integrando `marko` ou `mistune` para representação intermediária única.
  - [ ] Gerador nativo de `.epub` 3.0 com suporte a CSS Reflowable e metadados Dublin Core.
  - [ ] **Módulo EPUB3 ilustrado:** adaptar `src/epub_exporter.py` para consumir
    `plano_ilustracoes.yaml` e associar cada arte ao trecho narrativo correto,
    sem reproduzir as posições fixas ou os spreads do PDF.
  - [ ] Gerar abertura ilustrada, sequência responsiva de texto e imagens,
    reflexão e navegação própria para cada conto.
  - [ ] Incorporar imagens otimizadas para tela, capa, textos alternativos,
    ordem de leitura semântica e CSS responsivo para celular, tablet e e-reader.
  - [ ] Gerar sumário EPUB navegável, landmarks e metadados de acessibilidade.
  - [ ] Não usar números fixos de página no EPUB reflowable; preservar apenas a
    hierarquia e os links de navegação.
  - [ ] Criar testes do pacote EPUB antes de enviá-lo ao Projeto 5 — Ship.
- [ ] **v4.2.0 — Presets de Mangás e HQs**
  - [ ] Template Typst dedicado para leitura Right-to-Left (RTL), grids de painéis e onomatopeias em camadas SVG.
- [ ] **v4.3.0 — Interface Web & Preview em Tempo Real**
  - [ ] Dashboard Web em FastAPI + WebAssembly/Typst para visualização síncrona da diagramação.

---

## 📜 Licença

Distribuído sob a licença **MIT**. Veja `LICENSE` para mais detalhes.
