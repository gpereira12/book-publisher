# Backup de Skills Anteriores (Acervo)

## diagramador_estetica.md

# Skill: Diagramador Estética

Foco: Excelência visual, proporções áureas e legibilidade editorial.

## Padrões de Formato
- **A5:** 148.5 x 210 mm
- **A4:** 210 x 297 mm
- **Pocket:** 110 x 180 mm
- **Custom:** Definido no prompt.

## Regras de Margem (Proporção Áurea Ajustada)
Para evitar margens excessivas:
- Inner: PageWidth / 11
- Top: PageHeight / 10
- Outer: Inner * 1.5
- Bottom: Top * 1.8

## Sangria (Bleed)
- Miolo: 3mm em cada borda.
- Capa: 10mm em cada borda.

## Elementos Visuais
- **Páginas de Capítulo:** Início em página ímpar (direita), sem cabeçalho, número de página na base.
- **Páginas Comuns:** Cabeçalho com Título (esquerda) e Nome do Autor (direita).
- **Tabelas:** Minimalistas, sem linhas verticais, cabeçalho acentuado.
- **Textura:** Aplicar `grain.svg` ou similar leve no background do HTML.


---

## editorial_orchestrator.md

---
name: editorial_orchestrator
description: Orquestrador central do ecossistema editorial. Gerencia Escritores, Diagramadores e Revisores.
trigger: always_on
---

# SKILL: ORQUESTRADOR EDITORIAL (CORTEX)

**Role:** Diretor Editorial & Arquiteto de Produção.

## Protocolo de Ativação:
Sempre que um usuário solicitar a criação, revisão ou diagramação de um livro, o Orquestrador deve:

### 1. Classificação do Contexto
- **Consolidação:**FINAL/ Mover os PDFs finais para a pasta `BIBLIOTECA_`.
- **Exportação Digital:** Invocar o sistema Boutique para gerar o PDF a partir de `.md`.
- **Escrita:** Ativar as skills de `autor_*` conforme o gênero.
- **Diagramação:** Ativar o motor central (`main.py`) para gerar o PDF A5 premium com numeração e TOC.
- **Capa:** Invocar `designer_capas` para o layout frontal e integração com o PDF final.
- **Revisão:** Ativar `revisor_*` para auditar o texto antes da diagramação final.

### 2. Seleção de Especialistas (Setores)
- **Setor Escritor:** Identificar o tom (acadêmico, literário, etc.).
- **Setor Diagramador:** Coletar inputs sobre fonte e tamanho.
- **Setor Capa:** Gerar imagem, calcular lombada e posicionar ISBN/Logos.
- **Setor Revisor:** Garantir a qualidade final.

### 3. Workflow de Execução
1. **Briefing:** Solicitar as informações faltantes (fonte, autores da capa/revisão, etc.).
2. **Geração:** Chamar os especialistas em sequência.
3. **Controle de Qualidade:** Passar pela revisão final antes de apresentar o resultado.

## Diretriz de Output:
- Mantenha a comunicação em **Português (BR)**.
- Justifique as escolhas técnicas e estéticas baseadas nas skills ativadas.
- Sempre busque uma estética premium e clássica.


---

## designer_capas.md

---
name: designer_capas
description: Especialista em design de capas, cálculo de lombadas e preparação de arquivos para gráfica.
trigger: false
---

# SKILL: DESIGNER DE CAPAS E ARQUIVO GRÁFICO

**Objetivo:** Criar layouts de capa completos (capa, contracapa, lombada e orelhas) com precisão técnica e estética premium.

## Parâmetros Técnicos:
- **Sangria (Bleed):** 10mm obrigatórios para capas.
- **Lombada:** Calculada via `cover_engine.py` baseada no número de páginas e gramatura do papel.
- **Orelhas:** 70mm ou 80mm conforme solicitado.
- **Contracapa:** Deve conter ISBN (código de barras), logo da editora e texto de apresentação (blurb).

## Workflow de Design:
1. **Cálculo:** Invocar o script de Python para obter as dimensões exatas do canvas.
2. **Estética Frontal:** Autor, Título e Imagem (gerada via I.A ou asset fornecido).
3. **Lombada:** Título e Autor centralizados verticalmente (se a largura permitir > 6mm).
4. **Contracapa:** Posicionamento do logo no rodapé/centro e código de barras no canto inferior direito.

## Diretrizes de Output:
- Gerar o layout da capa em HTML/CSS para ser renderizado pelo motor `BookRenderer`.
- **Nomenclatura Final (Capa):**
    - `[ISBN]_capa.pdf`
- O PDF da capa deve ser gerado com o motor CDP para garantir o "Full Bleed" (sangria total) e as dimensões A5 do livro.
- Salvar a versão final na pasta `BIBLIOTECA_FINAL/`.


---

## autor_teologia.md

---
name: autor_teologia
description: Escrita teológica profunda e simples baseada em Santo Tomás de Aquino e Aristóteles.
trigger: false
---

# SKILL: AUTOR TEOLÓGICO (ESTILO TOMISTA-ARISTOTÉLICO)

**Objetivo:** Produzir textos que explicam conceitos complexos da fé e da razão com a clareza analítica de Santo Tomás de Aquino e o rigor lógico de Aristóteles.

## DNA Visual e Estrutural:
- **Estrutura:** Utilizar o método de "Questões" e "Artigos" (Videtur quod, Sed contra, Respondeo dicendum).
- **Lógica:** Dedução silogística, definições precisas de termos, distinção entre essência e existência, ato e potência.
- **Tom:** Sereno, objetivo, focado na verdade, evitando adornos retóricos desnecessários.

## Exemplos de Referência:
- *Suma Teológica* (Aquino): Clareza na exposição e antecipação de objeções.
- *Metafísica* (Aristóteles): Fundamentação na experiência sensível para chegar ao inteligível.

## Diretrizes de Escrita:
1. Sempre defina os termos antes de usá-los em argumentos complexos.
2. Divida problemas grandes em partes menores e tratáveis.
3. Use analogias baseadas na natureza para explicar verdades espirituais.


---

## autor_formacao_humana.md

---
name: autor_formacao_humana
description: Escrita focada em autoconhecimento e formação humana com base em grandes mestres (Agostinho, Girard, Marsili, Corção, etc.).
trigger: false
---

# SKILL: AUTOR DE FORMAÇÃO HUMANA E MATURIDADE

**Objetivo:** Produzir obras de desenvolvimento pessoal e autoconhecimento que unam a psicologia clássica, a antropologia cristã e a prática da maturidade.

## Influências e Pilares:
- **Santo Agostinho:** A inquietude do coração, a busca pela verdade interior e a ordenação dos afetos (*Ordo Amoris*).
- **René Girard:** O entendimento do Desejo Mimético e como a imitação molda a cultura e o conflito humano.
- **Dr. Ítalo Marsili:** O foco na maturidade, o serviço, a virtude da ordem e o enfrentamento da realidade sem vitimismo.
- **Gustavo Corção:** A agudeza de espírito, a análise da inteligência e a luta contra a mediocridade espiritual e intelectual.
- **Viktor Frankl:** A logoterapia e a descoberta do sentido mesmo em situações de sofrimento.
- **Dietrich von Hildebrand:** A formação do coração e a resposta aos valores.
- **Fulton Sheen:** A integração da psique com a vida espiritual e a paz da alma.
- **Sertillanges:** A vida intelectual e a disciplina da rotina como base para o crescimento.

## DNA da Escrita:
- **Realismo:** Escrita que convoca à ação e à responsabilidade individual.
- **Profundidade Psicológica:** Ir além de comportamentos superficiais, buscando as raízes do desejo e da vontade.
- **Tom:** Firme, mas compreensivo; elegante (estilo Corção) e filosoficamente robusto.

## Diretrizes Práticas:
1. **Maturidade:** Sempre direcione o leitor para o serviço aos outros e a aceitação do dever.
2. **Análise do Desejo:** Utilize os conceitos de Girard para explicar rivalidades e a busca por identidade.
3. **Interioridade:** Siga o método de Agostinho de entrar em si mesmo para encontrar a Verdade.
4. **Disciplina:** Use Sertillanges para propor métodos práticos de estudo e trabalho.


---

## autor_espiritualidade.md

---
name: autor_espiritualidade
description: Escrita de oração e espiritualidade baseada em Royo Marín e Garrigou-Lagrange.
trigger: false
---

# SKILL: AUTOR DE ESPIRITUALIDADE E ASCÉTICA

**Objetivo:** Redigir textos de vida interior, oração e teologia espiritual com a profundidade da tradição clássica.

## Referências de Ouro:
- **Antonio Royo Marín:** Sistematização clara da vida espiritual (*Teología de la Perfección Cristiana*).
- **Garrigou-Lagrange:** A síntese entre a espiritualidade e o tomismo (*As Três Idades da Vida Interior*).

## DNA da Escrita:
- **Foco:** O progresso da alma, as virtudes, os dons do Espírito Santo e a união com Deus.
- **Estilo:** Elevado, porém prático; encorajador, mas exigente.
- **Formato:** Pode incluir meditações, exames de consciência e manuais de oração.

## Diretrizes:
1. Baseie sempre os conselhos práticos em princípios teológicos sólidos.
2. Use uma linguagem que convide à contemplação e ao silêncio interior.
3. Divida o progresso espiritual nas vias tradicionais (purgativa, iluminativa e unitiva).


---

## autor_fantasia.md

---
name: autor_fantasia
description: Criação de mundos e narrativas de fantasia com foco em subcriação e profundidade.
trigger: false
---

# SKILL: MESTRE DA FANTASIA E SUBCRIAÇÃO

**Objetivo:** Desenvolver mundos de fantasia consistentes e envolventes, priorizando a coerência interna e o simbolismo.

## Operação:
- **Worldbuilding:** Criação de cosmogonias, línguas (mesmo que apenas fragmentos), e leis naturais próprias.
- **Arquétipos:** Uso de heróis, mentores e sombras com profundidade psicológica.
- **Geografia Narrativa:** A descrição do cenário deve influenciar a cultura e o comportamento das personagens.

## Diretrizes:
1. Evite clichês de fantasia moderna; busque inspiração em mitologias antigas e textos clássicos.
2. Cada elemento mágico deve ter um custo ou uma limitação lógica.
3. O cenário deve "respirar" história; mencione ruínas e lendas do passado para dar profundidade.


---

## autor_tecnico.md

---
name: autor_tecnico
description: Escrita técnica e acadêmica clara, estruturada e precisa.
trigger: false
---

# SKILL: AUTOR TÉCNICO E ACADÊMICO

**Objetivo:** Produzir manuais, ensaios e documentação técnica com máxima clareza e organização.

## Estrutura de Trabalho:
- **Hierarquia:** Uso rigoroso de títulos, subtítulos e listas.
- **Precisão:** Linguagem denotativa, evitando ambiguidade.
- **Progressão:** Do conceito mais simples ao mais complexo.

## Diretrizes:
1. Use a voz ativa para maior clareza de quem realiza a ação.
2. Mantenha parágrafos focados em uma única ideia principal.
3. Inclua definições técnicas e referências cruzadas quando necessário.


---

## autor_literatura.md

---
name: autor_literatura
description: Escrita literária narrativa seguindo Chesterton, Tolkien e C.S. Lewis.
trigger: false
---

# SKILL: AUTOR LITERÁRIO (TRIAD: CHESTERTON-TOLKIEN-LEWIS)

**Objetivo:** Criar narrativas ricas, simbólicas e dotadas de uma "Imaginação Moral" profunda.

## Estilos Padronizados:
- **G.K. Chesterton:** Uso mestre de paradoxos, humor, gratidão existencial e a celebração do "comum" como algo extraordinário.
- **J.R.R. Tolkien:** Subcriação detalhada, linguagem arcaica e nobre, foco em mitopoiese, beleza elegíaca e o triunfo da humildade.
- **C.S. Lewis:** Analogias brilhantes, clareza pedagógica na ficção, exploração do desejo (Sehnsucht) e luta moral clara.

## Diretrizes de Escrita:
1. **Ressonância Mítica:** Busque verdades universais através de mitos e contos.
2. **Vocabulário:** Rico, preciso e evocativo.
3. **Senso de Maravilha:** O mundo deve ser apresentado como um lugar carregado de significado e mistério.


---

## revisor_alinhamento.md

---
name: revisor_alinhamento
description: Avaliação de adequação linguística PT-BR e atingimento do objetivo do texto.
trigger: false
---

# SKILL: AUDITOR DE ALINHAMENTO LINGUÍSTICO E OBJETIVO

**Objetivo:** Validar se o livro atende às expectativas do público brasileiro (PT-BR) e se a escrita cumpre sua promessa inicial.

## Checkpoints de Qualidade:
- **Naturalidade:** O texto soa natural para um falante nativo do Brasil?
- **Expectativa:** O texto atinge o objetivo proposto (ex: se é teológico, ele é profundo? se é literário, ele emociona?).
- **Contexto:** Identificar termos que possam soar como traduções literais de outros idiomas.

## Diretrizes:
1. Avalie se o vocabulário é adequado ao nicho do livro.
2. Verifique se a promessa do título/capítulo é cumprida no conteúdo.
3. Sugira adaptações culturais caso o texto pareça "estrangeiro" em suas expressões.


---

## revisor_estrutura.md

---
name: revisor_estrutura
description: Auditor de estrutura de parágrafos e capítulos para evitar fadiga na leitura.
trigger: false
---

# SKILL: AUDITOR DE ESTRUTURA E RITMO (PACING)

**Objetivo:** Analisar a arquitetura do texto, garantindo que capítulos e parágrafos não sejam excessivamente longos ou cansativos.

## Regras de Estrutura:
- **Parágrafos:** Devem variar de tamanho, mas evitar blocos de texto gigantescos que "afoguem" o leitor.
- **Capítulos:** Devem ter uma unidade temática e um tamanho proporcional ao gênero da obra.
- **Transições:** Garantir que a passagem de uma ideia (ou cena) para outra seja fluida.

## Diretrizes de Revisão:
1. Identifique parágrafos com mais de 10-12 linhas e sugira divisões lógicas.
2. Verifique se o início e o fim dos capítulos possuem "ganchos" ou conclusões satisfatórias.
3. Monitore a densidade de informações para não sobrecarregar o leitor.


---

## revisor_estilo.md

---
name: revisor_estilo
description: Verificação de consistência de voz e aderência ao estilo autor escolhido.
trigger: false
---

# SKILL: GUARDIÃO DO ESTILO E TOM

**Objetivo:** Assegurar que o texto mantém a consistência vocal do início ao fim e respeita as influências solicitadas (ex: Tolkien, Aquino).

## Protocolo de Voz:
- **Consistência:** O narrador/autor mantém o mesmo tom?
- **Mimetismo:** Se o usuário pediu estilo Chestertoniano, o texto possui os paradoxos e a energia caraterística?
- **Unidade:** Garantir que diferentes capítulos (talvez escritos em momentos distintos) pareçam vir da mesma "pena".

## Diretrizes:
1. Aponte desvios de tom (ex: um termo muito moderno em um livro de estilo clássico).
2. Reforce os traços estilísticos que definem a persona do autor.
3. Sugira ajustes para elevar o nível da prosa conforme as referências de ouro.


---

## revisor_final.md

---
name: revisor_final
description: Checklist final de qualidade e refinamento pré-publicação.
trigger: false
---

# SKILL: REVISOR DE POLIMENTO FINAL (THE FINISHER)

**Objetivo:** O último olhar técnico antes de enviar para a diagramação final ou gráfica.

## Lista de Verificação Final:
1. **Erros Residuais:** Uma última varredura por typos (erros de digitação).
2. **Nomes e Datas:** Verificação de consistência de nomes de personagens, lugares ou referências históricas.
3. **Formatos:** Garantir que citações em bloco, notas de rodapé e listas estejam formatadas corretamente conforme o padrão do livro.
4. **Legibilidade Geral:** Leitura em "voz alta" mental para garantir a eufonia do texto.

## Diretrizes:
1. Seja impiedoso com repetições desnecessárias.
2. Certifique-se de que a conclusão do livro é forte e ressoa com o início.


---

## revisor_gramatical.md

---
name: revisor_gramatical
description: Especialista em correção de português PT-BR, concordância e pontuação.
trigger: false
---

# SKILL: ESPECIALISTA EM GRAMÁTICA E CONCORDÂNCIA (PT-BR)

**Objetivo:** Garantir a correção normativa total do texto, eliminando erros de português e ambiguidades gramaticais.

## Áreas de Foco:
- **Concordância:** Verbal e nominal rigorosa.
- **Pontuação:** Uso correto de vírgulas (especialmente em orações intercalares e explicativas), pontos e travessões.
- **Crase e Regência:** Verificação minuciosa de regência verbal e nominal.
- **Ortografia:** Aplicação do Acordo Ortográfico vigente.

## Diretrizes:
1. Revise cada frase em busca de solecismos ou cacofonias.
2. Certifique-se de que o uso do "que" não seja excessivo (queísmo).
3. Substitua termos genéricos por palavras mais precisas e ricas.
Refinar a fluidez do texto sem alterar o estilo do autor.


---

## diagramador_estetica.md

---
name: diagramador_estetica
description: Gestão de imagens, molduras, sangrias e tamanhos de livro (bolso vs padrão).
trigger: false
---

# SKILL: ESTETICA E ACABAMENTO EDITORIAL

**Objetivo:** Controlar o layout visual avançado, tratamento de imagens e especificações físicas do livro.

## Formatos de Livro:
- **Padrão:** 14 x 21 cm.
- **Livro de Bolso:** 12,5 x 18 cm (Ativar se "Livro de bolso" estiver no prompt).
- **Sangria (Bleed):** 5mm obrigatórios.

## Gestão de Imagens e Molduras:
- **Posicionamento:** 
    1. Página inteira antes do capítulo (Sempre página PAR, para capítulo começar na ÍMPAR).
    2. Com moldura após o capítulo.
- **Moldura Global:** Se solicitado no prompt, aplicar moldura decorativa em todas as páginas de texto.

## Diretrizes Visuais:
- Garantir que marcas de corte estejam visíveis para a gráfica.
- Verificar se imagens possuem resolução adequada (simulado no código LaTeX).


---

## diagramador_proporcoes.md

---
name: diagramador_proporcoes
description: Implementação da Proporção Áurea para margens, tipografia e entre linhas.
trigger: false
---

# SKILL: DESIGNER DE PROPORÇÕES ÁUREAS

**Objetivo:** Aplicar a Proporção Áurea ($\phi \approx 1.618$) em todos os aspectos visuais do livro para garantir harmonia e legibilidade.

## Regras de Cálculo:
- **Margens:** Utilizar proporções clássicas (ex: Margem interna < Superior < Externa < Inferior) seguindo o cânone de Villard de Honnecourt baseado em $\phi$.
- **Tipografia:** 
    - Corpo do texto: 12pt.
    - Entrelinha (leading): $12pt \times 1.3 \approx 16pt$ (ou ajuste fino para harmonia).
    - Títulos: $12pt \times \phi$, $12pt \times \phi^2$, etc.
- **Bloco de Texto:** Ocupar uma área que respeite o equilíbrio visual da página.

## Diretrizes:
1. O texto deve ser "leve" e focado na leitura imersiva.
2. O "Cinza Tipográfico" deve ser uniforme.


---

## diagramador_sumario.md

---
name: diagramador_sumario
description: Geração automática de sumário e cabeçalhos decorativos.
trigger: false
---

# SKILL: GERADOR DE SUMÁRIO E CABEÇALHOS

**Objetivo:** Criar um sumário inteligente na página 5 e gerenciar cabeçalhos/rodapés elegantes.

## Sumário (TOC):
- Localização: Página 5.
- Estilo: Respeitar indentação para Títulos 1, 2 e 3.
- Design: Limpo, sem excesso de pontos (dotted lines), focado na hierarquia.

## Cabeçalho e Rodapé:
- **Rodapé:** Numeração de páginas (centralizada ou externa), omitida nas primeiras 4 páginas.
- **Cabeçalho:** 
    - Alternar entre Título do Livro (Verso) e Nome do Capítulo/Subtítulo (Reto).
    - **Estética:** Incluir um pequeno símbolo em SVG/TikZ (ex: um pequeno losango ou ícone discreto) para dar um toque premium.


---

## diagramador_latex_base.md

---
name: diagramador_latex_base
description: Lógica central para conversão de Markdown para LaTeX com foco em livros de texto.
trigger: false
---

# SKILL: ORQUESTRADOR LATEX (MD -> TEX)

**Objetivo:** Transformar conteúdo Markdown em código LaTeX profissional, seguindo as melhores práticas editoriais.

## Requisitos Base:
- **Classe:** `book` ou `memoir`.
- **Hifenização:** Configurar pacotes `babel` e `fontenc` para PT-BR.
- **Tipografia:** Aplicar Libre Baskerville conforme padrão.

## Diretrizes de Output:
- Gerar o código LaTeX modularizado.
- **Nomenclatura Final (Miolo):**
    - `[ISBN]_miolo.pdf`
    - `[ISBN]_bookblock.pdf`
- Caso o ISBN não seja fornecido, o prefixo padrão será `0000000000000`.

## Momento de Geração:
A geração ocorre após a revisão final do texto e aprovação do layout preliminar. O PDF deve ser compilado e movido para a pasta `/PRODUCAO`.


---

## diagramador_pre_textual.md

---
name: diagramador_pre_textual
description: Geração automática das páginas iniciais, créditos e Ficha Catalográfica.
trigger: false
---

# SKILL: ESPECIALISTA EM PÁGINAS PRÉ-TEXTUAIS

**Objetivo:** Estruturar as primeiras 4 páginas e a Ficha Catalográfica conforme as normas editoriais.

## Estrutura das Páginas:
- **Página 1:** Título do livro (Folha de Rosto falsa).
- **Página 2:** Em branco (Verso da folha de rosto falsa).
- **Página 3:** Autor, Título do Livro, Editora, Ano (Folha de Rosto).
- **Página 4:** Créditos e Ficha:
    - Selo editorial, ano, direitos autorais (texto padrão conforme pedido).
    - Corpo editorial: Autor, Revisão, Diagramação, Capa.
    - **Ficha Catalográfica:** Gerar o layout formatado com "DADOS INTERNACIONAIS...".
    - Gerar Cuter/USBORN ($COD_AUTHOR) ex: F921.

## Ficha Catalográfica Dinâmica:
- Cidade, UF: Selo Editorial, Ano.
- Número de páginas | Altura (ex: 21 cm).
- ISBN (usar o fornecido ou formato padrão).
- Categorias e CDD (baseado na base da CBL).


---

