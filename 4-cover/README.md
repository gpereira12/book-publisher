# 🎨 Cover — Projeto 4 (Capas & Artes): Cover & Asset Generation Engine

Este projeto é o motor de geração de capas gráficas e artes do **Hub Editorial**. Ele lê o número exato de páginas gerado pelo **Layout (Projeto 3 — Diagramação)** e constrói a **Capa Horizontal Aberta Completa** para gráfica. Os renderizadores atuais geram PDF em RGB; a conversão CMYK deve usar o perfil ICC fornecido pela gráfica e é sinalizada pelo preflight.

---

## 🏛️ Funcionalidades

1. **Cálculo Matemático da Lombada (`spine_calculator.py`)**: Calcula a espessura da lombada baseando-se na contagem real de páginas do PDF e no tipo de papel.
2. **Suporte a Brochura & Capa Dura**:
   - *Brochura:* Inclui Orelhas de 70mm e sangria de 10mm.
   - *Capa Dura:* Inclui Vira de 35mm e Calhas de 10mm.
3. **Motor Duplo (`design_engine/`)** — `main.py` roteia automaticamente entre os dois motores conforme `book_config.yaml`:
   - **Motor A — HTML5/CSS3 + Playwright** (`engine_html.py`): capas ilustradas/full-bleed com imagem, em 3 padrões de composição (`layout_patterns/`: Full-Bleed, Split/Tarja, Moldura/Medalhão).
   - **Motor B — Typst** (`engine_typst.py`): presets minimalistas/tipográficos sem imagem, gerados via Typst compilado em `outputs/<livro>/capas/capa_horizontal_grafica.pdf`.
   - `design_engine/cover_spec.py` resolve uma única geometria canônica para os dois motores, incluindo sangria, orelhas/viras, calhas e área segura.
   - Paletas/fontes por gênero (`design_tokens.py`) são compartilhadas pelos dois motores.
4. **Código de Barras EAN-13 (`barcode_generator.py`)**: gerador de vetor SVG hand-rolled a partir do ISBN, usado por ambos os motores.
5. **Preflight (`design_engine/preflight.py`)**: valida configuração, ISBN, PDF do miolo, resolução efetiva, lombada e assets, além de gerar uma prova geométrica SVG.
6. **Estratégia antes do layout**: `EditorialBrief`, plano cromático 70/20/10 e `CompositionPlan` explicável selecionam hierarquia, zona de título, padrão e densidade ornamental.
7. **Prepress (`design_engine/prepress.py`)**: inspeciona MediaBox, fontes incorporadas, OutputIntent, boxes de corte/sangria, marcadores RGB/CMYK e perfil ICC.

> `4-cover/templates_typst/cover_base.typ` é um protótipo de terceiro motor (capa Typst com imagem full-bleed real) que ficou órfão — não é chamado por nenhum código ativo. Mantido apenas como referência para uma futura variante "Typst ilustrado".

---

## 🚀 Como Executar

```bash
python 4-cover/main.py --book-dir cronicas_chinesas_para_pequenos_guerreiros
```

## Preflight antes da gráfica

```bash
python 4-cover/main.py \
  --book-dir cronicas_chinesas_para_pequenos_guerreiros \
  --preflight
```

São gravados em `outputs/<livro>/capas/`:

- `preflight.json`, com erros, avisos, assets e geometria resolvida;
- `prova_geometria.svg`, com todos os painéis e áreas seguras.

Use `--strict` para retornar erro também quando houver avisos. A geração normal rejeita configurações estruturalmente inválidas e o código de barras rejeita ISBN com dígito verificador incorreto.

## Chaves geométricas e de composição

```yaml
sangria_mm: 10
area_segura_mm: 8
orelha_mm: 70       # brochura com orelhas
vira_mm: 35         # capa dura
calha_mm: 10        # capa dura

composicao_capa: true
ilustracao_bruta: assets/illustration_raw.png
fade_direction: bottom
fade_start: 0.5
foco_x: 0.5         # 0 = esquerda, 1 = direita
foco_y: 0.35        # 0 = topo, 1 = base
```

O compositor usa crop proporcional em vez de esticar a arte. `foco_x` e `foco_y` determinam qual região é preservada no enquadramento.

A hierarquia tipográfica do HTML parte de uma escala modular próxima de φ: base de 10,5 pt, heading de 17 pt e display de 27,5 pt. O padrão 3 recebe uma pequena correção óptica por ter moldura e menos área livre.

Para uma renderização reprodutível sem depender de Google Fonts, forneça os três papéis tipográficos com arquivos licenciados:

```yaml
fontes_locais:
  title: resources/fonts/titulo.ttf
  body: resources/fonts/corpo.ttf
  tag: resources/fonts/apoio.ttf
font_typst: "Nome interno da fonte"  # quando usar o motor Typst
```

## Testes

```bash
python -m unittest discover -s 4-cover/tests -v
```

## Direções visuais e variantes

Gere três direções de prompt — figurativa, simbólica e gráfica — já na proporção real do livro:

```bash
python 4-cover/generate_prompts_cli.py --book-dir <livro> --directions
```

Compare os três padrões de composição em uma única prancha:

```bash
python 4-cover/generate_variants_cli.py --book-dir <livro>
```

O comando grava os previews, `ranking.json` e `prancha_comparativa.jpg` em `outputs/<livro>/capas/variantes/`. A pontuação considera somente sinais verificáveis, como ruído visual na área do título e completude do conteúdo; a decisão estética continua humana.

Cada padrão mantém um PNG técnico com sangria e produz também um arquivo `_aparado.png`. A prancha usa a versão aparada, correspondente ao que o leitor verá depois do corte; o PDF de gráfica continua com a sangria exigida para produção.

## Brief, composição e regra 70/20/10

O diagnóstico anterior à renderização é gerado com:

```bash
python 4-cover/cover_strategy_cli.py --book-dir <livro>
```

Ele grava `estrategia_capa.json` com quatro blocos independentes: brief editorial, plano cromático, plano de composição e geometria. O brief mede sua própria completude e não considera a direção de arte pronta enquanto faltarem campos estratégicos.

```yaml
promessa_central: "..."
emocao_primaria: "..."
publico_visual: "..."
simbolos_chave: ["..."]
elementos_proibidos: ["..."]
diferencial_de_prateleira: "..."

proporcao_cores:
  dominante: 70
  secundaria: 20
  destaque: 10
cor_secundaria: "#7A3043"
cor_destaque: "#DBB666"

composicao_inteligente: true
ornamentos_complexidade: 4  # 1..5
ornamentos_densidade: moderada
```

70/20/10 representa papéis de dominância, não uma obrigação de medir cada pixel: dominante cria atmosfera e grandes campos; secundária estrutura tarjas e profundidade; destaque fica reservado para título, ornamentos e focos.

## SVG paramétrico

`design_engine/parametric_svg.py` fornece repetição linear, simetria radial, rosetas multicamadas e faixas meandro. Os níveis de 1 a 5 aumentam repetições e detalhes mantendo o SVG determinístico e editável.

```bash
python 4-cover/generate_ornament_catalog_cli.py --book-dir <livro>
```

O catálogo exporta divisor, canto, medalhão, faixa e roseta em cada nível para `assets/ornaments/catalog/`.

## Lettering vetorial de título

O modo `titulo_lettering_modo: vetorial` pode usar lockups exclusivos, nos quais as linhas, a palavra de impacto e os swashes são tratados separadamente:

```yaml
titulo_lettering_modo: vetorial
titulo_lettering_estilo: imperial_ruyi # pincel_celestial | selo_monumental
```

```bash
python 4-cover/generate_lettering_variants_cli.py --book-dir <livro>
```

O resultado permanece SVG editável. É um lettering editorial exclusivo do título, não uma fonte completa para composição de outros textos.

## Prepress

Depois da renderização:

```bash
python 4-cover/prepress_cli.py \
  --book-dir <livro> \
  --cover-pdf outputs/<livro>/capas/capa_padrao_2.pdf
```

O relatório `prepress.json` separa erros bloqueantes, avisos e confirmações. A conversão CMYK/PDF-X não é presumida: ela permanece bloqueada até a gráfica fornecer `perfil_icc_saida` e sua especificação de PDF/X.
