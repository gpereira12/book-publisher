<div align="center">

# 📚 Boutique de Livros

**Pipeline profissional de diagramação editorial: `Markdown → HTML → PDF`**

*Converte textos em livros com qualidade gráfica, prontos para gráfica ou publicação digital.*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-Headless_Chrome-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![Paged.js](https://img.shields.io/badge/Paged.js-CSS_Print_Polyfill-orange?style=flat-square)](https://pagedjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## Visão Geral

A **Boutique de Livros** é um sistema de diagramação editorial automatizado que transforma arquivos Markdown em PDFs profissionais — com capa, folha de rosto, sumário, numeração de página e suporte a múltiplos formatos físicos (A5, A4, Pocket).

O pipeline funciona em três etapas encadeadas:

```
texto_original.md
       │
       ▼
  [1] Parser (src/parser.py)
  ├── Lê e pré-processa o Markdown
  ├── Converte para HTML com python-markdown
  ├── Identifica capítulos, checklists e tabelas
  └── Otimiza imagens via Pillow (evita OOM no Chromium)
       │
       ▼
  [2] Builder (src/builder.py)
  ├── Gera HTML completo com CSS tipográfico profissional
  ├── Incorpora Paged.js para paginação tipo InDesign
  ├── Suporta 2 saídas: versão gráfica (com bleed/marcas de corte) e digital
  └── Imagens embutidas em base64 para portabilidade
       │
       ▼
  [3] PDF Printer (src/pdf_printer.py)
  ├── Abre o HTML via Playwright (Chromium headless)
  ├── Aguarda Paged.js renderizar a paginação
  ├── Exporta o PDF nativo via CDP
  └── Fallback automático para CLI do Chrome se necessário
```

---

## Funcionalidades

| Funcionalidade | Detalhe |
|---|---|
| 📄 **Formatos de livro** | A5 (148.5×210mm), A4, Pocket (125×180mm) |
| 🎨 **Temas** | Fundo Creme (`#FDF5E6`) ou Branco |
| 🖼️ **Capa automática** | Imagem embutida em base64, sem fontes externas |
| 📑 **Sumário automático** | Gerado via Paged.js com números de página reais |
| 📐 **Versão gráfica** | Inclui `bleed: 5mm` e marcas de corte para gráfica offset |
| 📱 **Versão digital** | Sem marcas, limpa, pronta para KDP/e-readers |
| 🔄 **Tabelas rotacionadas** | Tabelas largas são exibidas na horizontal (landscape) automaticamente |
| ☑️ **Checklists** | Sintaxe `* [ ]` / `* [x]` convertida para checkboxes elegantes |
| ⏱️ **Tempo de leitura** | Calculado por capítulo (200 palavras/min) |
| 🛡️ **Fallback robusto** | Se o Playwright crashar (OOM), usa CLI nativo do Chrome |

---

## Estrutura do Projeto

```
boutique-de-livros/
│
├── main.py                    # Ponto de entrada — orquestra o pipeline completo
├── inspect_pdf.py             # Utilitário para inspecionar metadados de PDFs gerados
├── requirements.txt           # Dependências Python
│
├── src/
│   ├── parser.py              # Markdown → HTML + otimização de imagens
│   ├── builder.py             # HTML → HTML completo (CSS tipográfico + Paged.js)
│   └── pdf_printer.py         # HTML → PDF via Playwright + Fallback CLI
│
├── inputs/
│   └── <nome_do_livro>/
│       ├── texto_original.md  # Conteúdo do livro em Markdown
│       └── assets/            # Imagens, capas, arabescos, QR codes…
│
├── branding_system/           # Templates de prompts para geração de imagens com IA
│   └── prompts/               # Prompts por dia (para livros de 33 dias)
│
└── resources/
    └── logos/                 # Logotipos das editoras (Ilios, CIA de Jesus, Coala…)
```

---

## Instalação

### Pré-requisitos

- Python **3.10+**
- `pip`

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/gpereira12/book-publisher.git
cd book-publisher

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Instale as dependências Python
pip install -r requirements.txt

# 4. Instale o browser do Playwright
playwright install chromium
```

---

## Uso

### Modo interativo

```bash
python main.py
```

O sistema vai perguntar passo a passo: nome do livro, formato, tema, autor, título e capa.

### Modo linha de comando (não-interativo)

```bash
python main.py \
  --book-dir O_Olhar_Elevado \
  --format A5 \
  --theme Creme \
  --author "Carolina Cordaro" \
  --title "O Olhar Elevado" \
  --cover inputs/O_Olhar_Elevado/assets/capa_olhar_elevado_v2.png
```

### Flags disponíveis

| Flag | Descrição |
|---|---|
| `--book-dir` | Nome da pasta dentro de `inputs/` |
| `--format` | `A5` (padrão), `A4`, `Pocket` |
| `--theme` | `Creme` (padrão) ou `Branco` |
| `--author` | Nome do autor |
| `--title` | Título do livro |
| `--cover` | Caminho para a imagem de capa |
| `--digital-only` | Gera apenas o PDF digital |
| `--print-only` | Gera apenas o PDF para gráfica |

### Saída

```
outputs/
└── O_Olhar_Elevado/
    ├── O_Olhar_Elevado_digital.pdf    # Para KDP, e-readers, envio digital
    └── O_Olhar_Elevado_impresso.pdf   # Para gráfica (com sangria e marcas de corte)
```

---

## Formatação do Markdown

O sistema reconhece convenções especiais no Markdown do livro:

```markdown
# Capítulo 1 — Título Principal
## Subcapítulo

> Texto de epígrafe (exibido alinhado à direita, itálico)

Parágrafo normal com texto justificado...

### Lista de Verificação

* [ ] Item pendente
* [x] Item concluído

### Tabela com Rotação Automática

| Coluna A | Coluna B | Coluna C |
|----------|----------|----------|
| ...      | ...      | ...      |
```

> **Dica:** Tabelas precedidas de um título são automaticamente detectadas e renderizadas em modo *landscape* (página horizontal).

---

## Livros Publicados com Este Sistema

| Livro | Autora | Formato |
|---|---|---|
| O Olhar Elevado | Carolina Cordaro | A5 Creme |
| A Mãe Forte | — | A5 Creme |
| As Virtudes do Pai | — | A5 Creme |

---

## Roadmap — Próximas Melhorias

> Funcionalidades planejadas para as próximas versões da Boutique de Livros.

### 🔥 v4.0 — Motor & Qualidade

- [ ] **Migrar de `PyPDF2` para `pypdf`** — biblioteca ativamente mantida, com melhor suporte a metadados e criptografia
- [ ] **Geração de metadados PDF/A** — embutir título, autor, ISBN, editora e palavras-chave no `DocumentInfo` do PDF para conformidade editorial
- [ ] **Suporte a hifenização** — integrar `pyphen` para hifenização automática em pt-BR, eliminando rios de espaço no texto justificado
- [ ] **Cache de imagens otimizadas** — salvar hash de cada imagem otimizada e reutilizar entre builds, reduzindo tempo de geração em ~40%

### 🎨 v4.1 — Templates & Temas

- [ ] **Gerador de Código de Barras (EAN-13 / ISBN)** — geração automática de vetor de código de barras a partir do código ISBN/EAN para posicionamento na contracapa do livro
- [ ] **Sistema de temas via YAML** — definir paleta de cores, fontes, margens e espaçamentos em arquivos `.yaml` por livro, sem tocar no Python
- [ ] **Novos formatos físicos** — suporte a `Trade Paperback` (152×228mm) e `Letter` (8.5"×11")
- [ ] **Página de direitos autorais** — geração automática de folha de créditos (CIP, ISBN, Copyright, edição)
- [ ] **Cabeçalhos de página (running headers)** — exibir título do capítulo atual no topo das páginas ímpares

### 🤖 v4.2 — Inteligência Artificial

- [ ] **Geração de capa com IA** — integração nativa com API da OpenAI (DALL-E) ou Stability AI, usando os prompts já estruturados em `branding_system/`
- [ ] **Sugestão de título via LLM** — analisar o texto e sugerir títulos e subtítulos alternativos
- [ ] **Revisão gramatical automatizada** — passar o Markdown pelo LanguageTool (pt-BR) antes da diagramação e exibir um relatório de sugestões

### 🌐 v4.3 — Interface & Distribuição

- [ ] **Interface Web (FastAPI + React)** — painel de controle com upload de Markdown, preview ao vivo do HTML e download dos PDFs
- [ ] **CLI com Rich** — substituir os `print()` simples por uma TUI elegante usando a biblioteca `rich` (progress bars, tabelas, cores)
- [ ] **Exportação para EPUB** — gerar `.epub` a partir das seções já parseadas, para publicação em lojas digitais (Kobo, Apple Books)
- [ ] **Integração com KDP** — verificação automática das especificações de tamanho, resolução e sangria da Amazon KDP

### 🏗️ v4.4 — Arquitetura & DevOps

- [ ] **Testes automatizados** — suite `pytest` cobrindo o parser (Markdown → seções), o builder (HTML gerado) e a impressão (PDF gerado e não corrompido)
- [ ] **GitHub Actions** — CI que roda os testes a cada push e valida que o PDF do livro de exemplo é gerado com sucesso
- [ ] **Docker** — imagem Docker com Python + Playwright + fontes Google pré-instaladas, eliminando dependências de sistema
- [ ] **Plugin de configuração por livro** — arquivo `book.yaml` dentro de cada pasta `inputs/<livro>/` com todas as configurações, sem precisar de flags no CLI

---

## Contribuindo

1. Fork o repositório
2. Crie sua branch: `git checkout -b feature/minha-melhoria`
3. Commit: `git commit -m 'feat: minha melhoria'`
4. Push: `git push origin feature/minha-melhoria`
5. Abra um Pull Request

---

## Licença

Distribuído sob a licença **MIT**. Veja [`LICENSE`](LICENSE) para mais detalhes.

---

<div align="center">
  Feito com ☕ e tipografia por <a href="https://github.com/gpereira12">gpereira12</a>
</div>
