# Edit — sistema de revisão editorial

O Edit é o segundo estágio do Hub Editorial. Ele audita manuscritos Markdown,
registra achados rastreáveis e aplica somente correções mecânicas explicitamente
autorizadas. O sistema foi projetado como apoio à decisão editorial: uma métrica ou
heurística localiza pontos de atenção, mas não substitui leitura e julgamento humanos.

## Princípios

1. **Auditoria segura por padrão:** executar o comando normal não altera o manuscrito.
2. **Rastreabilidade:** todo achado recebe ID, regra, categoria, gravidade, confiança,
   capítulo, linha, trecho, explicação e sugestão.
3. **Automação conservadora:** apenas transformações mecânicas de alta confiança
   podem ser aplicadas automaticamente.
4. **Preservação:** antes de alterar `texto_revisado.md`, o sistema cria um backup.
5. **Configuração por livro:** metas editoriais pertencem ao `book_config.yaml`.
6. **Métrica não é veredito:** legibilidade, frequência ou densidade não medem,
   isoladamente, qualidade literária.
7. **Transparência:** o relatório informa limitações e não tenta determinar se um
   texto foi escrito por IA.

## Arquitetura

```text
texto_original.md / texto_revisado.md
                │
                ▼
       seleção segura da fonte
                │
                ▼
       regras e métricas editoriais
                │
                ▼
       contrato comum de Finding
                │
       ┌────────┴────────┐
       ▼                 ▼
relatório Markdown   achados JSON
       │
       ▼ somente com autorização
backup + correções seguras / versão datada
```

Componentes principais:

- `main.py`: orquestra modos, regras, relatórios, versões e integração com Layout.
- `review_models.py`: define o contrato comum dos achados e IDs estáveis.
- `rules/grammar.py`: regras gramaticais conservadoras e correções seguras.
- `rules/cohesion.py`: coesão referencial, conectores e transições locais.
- `rules/coherence.py`: fatos, estados e cronologia declarados para continuidade interna.
- `rules/factuality.py`: alegações, fontes, estados de verificação e termos temporais.
- `rules/structure.py`: requisitos estruturais declarados por livro e integridade Markdown.
- `rules/flesch_readability.py`: legibilidade global e local.
- `rules/style_dreyer.py`: palavras-muleta e frequência lexical.
- `rules/style_sheet.py`: grafia estrita e lista de anacronismos.
- `rules/typography.py`: normalizações tipográficas seguras.
- `rules/ai_patterns.py`: marcadores de prosa formulaica com análise de densidade.
- `tests/`: testes unitários e de preservação das revisões.

## Contrato dos achados

Cada ocorrência acionável é serializada aproximadamente assim:

```json
{
  "id": "REV-B3955C3E1B",
  "rule": "readability.section_below_target",
  "category": "legibilidade",
  "severity": "observacao",
  "confidence": 0.70,
  "chapter": "Prefácio",
  "line": 24,
  "excerpt": "Prefácio — Narração",
  "explanation": "A seção ficou abaixo da meta editorial configurada.",
  "suggestion": "Examinar os trechos mais densos.",
  "auto_fixable": false
}
```

Gravidades:

- `informacao`: contexto para o editor; não demanda mudança.
- `observacao`: merece leitura humana, sem bloquear o fluxo.
- `alerta`: revisão editorial recomendada.
- `erro`: correção objetiva pendente.
- `bloqueador`: o livro não deve avançar até a resolução.

A confiança representa a segurança da classificação automática, não a
importância literária do trecho.

## Modos de execução

```bash
# Auditoria: prefere texto_revisado.md quando ele existe e não altera manuscritos
python 2-edit/main.py --book-dir meu_livro

# Auditar explicitamente o original
python 2-edit/main.py --book-dir meu_livro --audit --source original

# Aplicar normalizações mecânicas; cria backup antes de escrever
python 2-edit/main.py --book-dir meu_livro --apply-safe-fixes

# Criar uma versão datada sem alterar o manuscrito ativo
python 2-edit/main.py --book-dir meu_livro --create-revision

# Comparar original e revisado
python 2-edit/main.py --book-dir meu_livro --compare

# Aplicar correções seguras e, depois, executar o Layout
python 2-edit/main.py --book-dir meu_livro --apply-safe-fixes --auto-approve
```

`--auto-approve` exige `--apply-safe-fixes`. Isso impede que a diagramação use uma
revisão desatualizada ou não confirmada.

## Frameworks e referências editoriais

### Flesch adaptado ao português

A legibilidade usa a fórmula:

```text
248,835 - 1,015 × palavras por frase - 84,6 × sílabas por palavra
```

A contagem de sílabas é uma aproximação por grupos vocálicos. As faixas etárias
exibidas são referências editoriais aproximadas, não certificação pedagógica.

### Princípios inspirados em Benjamin Dreyer

O sistema procura uma lista em português de intensificadores e palavras-muleta,
como `muito`, `realmente` e `na verdade`. Trata-se de uma regra inspirada na busca
de economia verbal associada a Dreyer, não de uma implementação integral de sua obra.

### Folha de estilo editorial

O `style_sheet.yaml` funciona como manual de decisões do livro: grafias canônicas,
variantes proibidas e termos que pedem verificação histórica. Esse é um mecanismo
tradicional de copyediting adaptado para validação determinística.

### Convenções tipográficas do português brasileiro

As regras atuais normalizam travessões, espaços e capitalização de verbos de
elocução depois da fala. Apenas casos mecânicos e de alta confiança são
autocorrigíveis.

### Heurística própria de prosa formulaica

Detecta antíteses espelhadas, anúncios metatextuais, perguntas retóricas respondidas,
anáforas e excesso de travessões parentéticos. A classificação considera densidade,
ignora anáforas em diálogos e aceita ocorrências isoladas como recurso literário.
Não é um detector de autoria por IA.

### Análise lexical

A frequência é calculada com tokenização simples, tamanho mínimo de palavra e uma
lista de palavras funcionais ignoradas. Frequência global é uma pista, não um erro.

### Referências ainda não implementadas

A recomendação de corte de 10% associada a Stephen King foi mencionada em versões
anteriores da documentação, mas ainda não existe como regra executável. Ela não é
apresentada como funcionalidade atual.

O motor não usa modelo de linguagem, classificador de autoria ou framework externo
de NLP durante a execução. A implementação utiliza Python, expressões regulares,
estruturas da biblioteca padrão e PyYAML para configuração. A pesquisa humana pode
consultar fontes externas e então registrar a evidência no YAML; a auditoria local
é reproduzível e não depende de acesso à internet.

## Ponto 1 — gramática e correção linguística

Status: **validado editorialmente**.

O framework combina gramática normativa do português brasileiro, regras editoriais
determinísticas e a variante configurada para o livro. Ele separa os achados em:

- ortografia de formas conhecidas;
- concordância verbal de construções impessoais;
- regência de padrões de alta confiança;
- crase em locuções fixas;
- emprego de pronomes depois de preposição ou antes de infinitivo;
- espaçamento de pontuação;
- palavras duplicadas acidentalmente;
- balanceamento de parênteses e aspas curvas.

Exemplo de configuração:

```yaml
revisao:
  gramatica:
    variante: pt-BR
    nivel: conservador
    max_itens_relatorio: 100
    preservar_desvios_dialogo: true
    ignorar_regras: []
```

Interpretação:

- `variante`: norma linguística adotada pelo livro.
- `nivel`: no modo `conservador`, somente padrões de alta confiança são sinalizados.
- `max_itens_relatorio`: limita a apresentação, sem mudar a contagem total.
- `preservar_desvios_dialogo`: impede que marcas possivelmente intencionais da fala
  sejam corrigidas sem decisão humana; espaçamento mecânico de pontuação continua seguro.
- `ignorar_regras`: permite desativar uma regra incompatível com o projeto.

Exemplos autocorrigíveis somente com `--apply-safe-fixes`:

- `concerteza` → `com certeza`;
- `derrepente` → `de repente`;
- `à partir` → `a partir`;
- `a medida que` → `à medida que`;
- formas anteriores ao Acordo Ortográfico, como `idéia` → `ideia`;
- espaço indevido antes de vírgula.

Exemplos que exigem leitura humana:

- `fazem dois anos`;
- `haviam muitas pessoas`, quando `haver` significa existir;
- `preferir X do que Y`;
- `para mim fazer`;
- `a gente fomos`, `nós vai` e `eles foi`, especialmente em diálogos;
- `obedecer o mestre`, cuja solução depende do complemento e da crase;
- palavra repetida em fala ou recurso enfático.

O relatório identifica se cada ocorrência está em `prosa` ou `dialogo`. Com a
preservação de diálogos ativa, desvios de ortografia e concordância em falas perdem
gravidade e deixam de ser autocorrigíveis, pois podem caracterizar uma personagem.

O módulo não afirma oferecer correção gramatical completa. Não existe no ambiente
atual um dicionário ortográfico abrangente nem um analisador sintático do português;
concordância, regência, crase e pontuação frequentemente dependem de sentido.
A ausência de achados significa apenas que as regras implementadas não encontraram
problemas.

## Ponto 2 — coesão e conexão de ideias

Status: **validado editorialmente**.

O framework combina coesão referencial e sequencial com heurísticas editoriais
locais. O objetivo é localizar pontos em que as frases podem estar corretas
isoladamente, mas a ligação entre elas pede confirmação.

A cobertura atual inclui:

- pronomes pessoais com mais de um referente recente plausível;
- entidades e aliases configuráveis por livro;
- fusão de nome, título, aposição e predicativo que designam a mesma pessoa;
- pares redundantes como `mas porém` e `portanto logo`;
- sobreposição de concessão e adversidade, como `embora ..., mas ...`;
- três ou mais frases consecutivas iniciadas pelo mesmo conector;
- classificação funcional dos conectores: adversidade, causa, conclusão,
  adição, tempo, condição, concessão e explicação;
- densidade de conectores iniciais por mil palavras;
- distinção entre prosa e diálogo.

Exemplo de configuração:

```yaml
revisao:
  coesao:
    min_repeticoes_conector: 3
    max_itens_relatorio: 100
    ignorar_regras: []
    entidades:
      personagem_a:
        genero: masculino
        aliases: ["Nome", "Título do Nome"]
```

As entidades pertencem ao livro, não ao motor. O motor fornece o mecanismo genérico;
cada `book_config.yaml` registra nomes, aliases e gênero gramatical necessários para
avaliar referências pronominais.

Nenhum achado de coesão é autocorrigível. Substituir um pronome, retirar um conector
ou reconstruir uma transição pode alterar foco, ritmo e sentido. O sistema apresenta
a pergunta editorial e a decisão permanece humana.

Limitações:

- a resolução pronominal usa contexto local, não compreensão semântica completa;
- referentes implícitos e conhecimento de mundo ainda não são modelados;
- variedade de conectores não garante progressão lógica;
- conexões semanticamente incorretas serão aprofundadas no ponto 3, coerência.

## Ponto 3 — coerência e continuidade interna

Status: **validado editorialmente**.

O framework usa um **registro de continuidade narrativa** com restrições declarativas.
O motor fornece mecanismos genéricos e cada livro configura apenas os fatos e eventos
que deseja acompanhar. Assim, nenhuma estrutura própria dos Contos Chineses fica
chumbada no código.

A cobertura executável inclui:

- afirmação incompatível depois de uma mudança terminal, como personagem morto que
  volta a agir ou objeto quebrado que reaparece intacto;
- ordem de marcos narrativos, como partida, retorno e consequência;
- fatos quantificados repetidos com valores incompatíveis;
- escopo por livro, capítulo ou seção;
- números escritos por extenso ou com algarismos;
- regras ignoráveis por projeto;
- contagem dos eventos realmente encontrados, para que `zero achados` não seja
  confundido com `nenhuma regra executada`.

Exemplo genérico:

```yaml
revisao:
  coerencia:
    max_itens_relatorio: 100
    ignorar_regras: []
    estados:
      - id: personagem_apos_morte
        escopo: capitulo
        padroes_terminais: ['\bAna morreu\b']
        padroes_incompativeis: ['\bAna caminhou\b']
    sequencias:
      - id: viagem
        escopo: capitulo
        marcos:
          - id: partida
            padroes: ['\bpartiu\b']
          - id: chegada
            padroes: ['\bchegou\b']
    fatos_numericos:
      - id: numero_de_filhos
        escopo: livro
        padroes:
          - '\b(?P<valor>sete|7) filhos\b'
          - '\b(?P<valor>oito|8) irmãos\b'
```

As expressões pertencem à configuração do livro. O grupo nomeado `valor` identifica
o número que deve permanecer consistente. Os achados nunca são autocorrigíveis:
uma aparente contradição pode ser lembrança, sonho, narrador não confiável, salto
temporal ou mudança deliberada.

O módulo não promete compreensão semântica integral. Continuam exigindo leitura
humana: motivação e causalidade, objetivos das personagens, cronologia implícita,
geografia e deslocamentos, objetos e ferimentos, regras do mundo narrativo, além de
promessas e resoluções. Factualidade externa e anacronismos pertencem ao ponto 4.

## Ponto 4 — factualidade, fontes, anacronismos e sustentação

Status: **validado editorialmente**.

O framework combina **registro de alegações**, **proveniência de fontes** e
**restrições temporais configuráveis**. O motor diferencia:

- fato histórico verificável;
- tradição, lenda ou provérbio com origem textual;
- adaptação ou ficção deliberada;
- alegação imprecisa, contestada ou ainda não verificada;
- termo incompatível com o período narrativo;
- uso moderno legítimo em prefácio ou reflexão.

Uma obra ficcional não precisa provar seus elementos inventados. A sustentação passa
a ser necessária quando o próprio texto apresenta algo como histórico, clássico,
tradicional ou factual. A classificação evita que magia, metáforas e personagens
inventadas sejam tratadas automaticamente como erros.

Exemplo reduzido:

```yaml
revisao:
  factualidade:
    fontes:
      fonte_primaria:
        titulo: "Título e seção da obra"
        url: "https://exemplo.org/fonte"
        tipo: primaria
        acesso: "2026-08-09"
    alegacoes:
      - id: origem_do_conto
        natureza: tradicao
        status: verificada
        padroes: ['Baseado no provérbio']
        fontes: [fonte_primaria]
    termos_temporais:
      - id: tecnologia_moderna
        padroes: ['\btecnologia moderna\b']
        ignorar_secoes: ["Reflexão"]
        fontes: [fonte_primaria]
```

Estados usuais de uma alegação:

- `verificada`: a formulação é compatível com a evidência cadastrada;
- `adaptada`: invenção ou transformação está assumida com transparência;
- `imprecisa`: há base, mas a frase exagera ou distorce seu alcance;
- `contestada`: fontes relevantes divergem;
- `nao_verificada`: a origem ou afirmação ainda não possui sustentação suficiente;
- `fonte_incompativel`: a fonte trata de tema próximo, mas não sustenta a narrativa;
- `rotulo_enganoso`: ficção legítima está apresentada como tradição específica.

Cada fonte deve possuir pelo menos título e URL. IDs inexistentes ou metadados
incompletos geram erro de configuração. O relatório registra quantas alegações e
termos foram realmente encontrados, impedindo que ausência de cobertura pareça
aprovação factual.

Hierarquia editorial recomendada:

1. texto primário ou edição crítica;
2. instituição pública, científica, museu ou universidade;
3. pesquisa acadêmica e obra especializada;
4. fonte secundária confiável;
5. página popular apenas como pista, nunca como sustentação única de alegação forte.

O mecanismo anterior de `termos_anacronicos_proibidos` da folha de estilo continua
compatível, mas é apenas uma lista lexical. O ponto 4 acrescenta contexto por seção,
evidência, natureza da alegação, grau de confiança e justificativa.

Nenhum achado factual é autocorrigível. Uma fonte pode exigir tradução, interpretação
ou delimitação histórica, e uma aparente imprecisão pode ser escolha consciente do
autor. O motor também não valida automaticamente se uma página da internet continua
correta; a data de acesso e a revisão humana permanecem necessárias.

## Ponto 5 — estrutura conforme o framework do livro

Status: **arquitetura validada; escopo visual delegado ao futuro projeto de ilustração**.

O framework usa **restrições estruturais declarativas** e verificações de integridade
Markdown. Não existe no código uma estrutura narrativa universal. Em particular, o
motor não exige introdução, conflito ou reflexão de todos os livros.

Cada projeto decide quais requisitos fazem sentido. A cobertura disponível inclui:

- correspondência entre o framework do `book_config.yaml` e o frontmatter;
- registro, quantidade, títulos e ordem dos capítulos;
- entradas ainda marcadas como pendentes no registro;
- capítulos excluídos das regras, como prefácio ou apêndice;
- hierarquia de títulos Markdown e títulos de capítulo duplicados;
- seções obrigatórias ou únicas escolhidas pelo projeto;
- presença configurável de atribuição, imagem e texto alternativo;
- mínimo de palavras por capítulo como sinal de completude;
- proporção configurável de uma seção dentro do capítulo.
- plano visual externo com contagem de capítulos, páginas e cenas;
- abertura em página única e spreads internos conforme o preset do livro;
- unicidade dos IDs e dos caminhos reservados para cada futuro ativo;
- bíblia visual multidisciplinar para compilação de prompts;
- duas fases distintas: `planejamento`, que valida os prompts sem exigir artes, e
  `producao`, que passa a exigir os arquivos aprovados.

O trabalho visual é opt-in e possui três presets. O motor consulta o preset antes de
ler planos, compilar prompts ou procurar ativos:

| `modo` | Comportamento |
|---|---|
| `sem_imagens` | Não carrega plano visual nem executa processamento de prompts. |
| `abertura_pagina_par` | Planeja uma ilustração na página par, em frente ao início do capítulo na página ímpar. |
| `totalmente_ilustrado` | Planeja abertura, quantidade adaptativa de spreads e texto integrado segundo a configuração do livro. |

Assim, o sistema de revisão continua genérico: um romance sem arte não paga o custo
do pipeline visual, um livro com frontispícios gera somente um prompt por capítulo e
um projeto ilustrado pode declarar uma estrutura mais extensa.

Configuração dos Contos Chineses:

```yaml
revisao:
  estrutura:
    framework_esperado: contos_parabolas_sabedoria
    capitulos_ignorados: ["Prefácio"]
    registro_capitulos:
      campo: historias
      campo_titulo: titulo
      valores_pendentes: ["Pendente"]
      permitir_pendentes: false
    secoes_obrigatorias: ["Reflexão"]
    secoes_unicas: ["Reflexão"]
    elementos_obrigatorios:
      atribuicao: true
      imagem: false
      texto_alternativo_imagem: false
      arquivo_imagem: false
    plano_ilustracoes:
      modo: totalmente_ilustrado
      gerar_prompts: true
      provedor_prompts: google_flow
      idioma_prompts: en
      arquivo: plano_ilustracoes.yaml
      fase: planejamento
      paginas_iniciais: 4
      quantidade_spreads: adaptativa
      min_spreads_por_capitulo: 3
      palavras_por_spread_referencia: 210
      tolerancia_superior_densidade: 1.25
      paginas_finais: 4
      inicio_capitulo_impar: true
      abertura_pagina_unica: true
      texto_integrado: true
    min_palavras_capitulo: 650
    proporcoes_secoes:
      Reflexão:
        min: 0.15
        max: 0.30
```

Aqui, a reflexão é obrigatória somente porque este livro é uma coletânea de parábolas
com comentário final. Um romance poderia deixar `secoes_obrigatorias` vazio; um manual
poderia exigir `Objetivos`, `Exercícios` e `Resumo`; um ensaio poderia validar apenas
a hierarquia Markdown.

Metas de extensão e proporção geram observações, não ordens de preenchimento. Um
capítulo curto pode estar completo e uma reflexão longa pode ser deliberada. Ausência
de texto alternativo também não autoriza descrição automática, pois o sistema não
deve inventar o conteúdo visual sem inspeção. Quando `arquivo_imagem` está ativo e o
diretório do livro é conhecido, referências locais quebradas também são reportadas.

### Modelo visual dos Contos Chineses

O mapa atual tem **64 páginas**, número compatível com cadernos de 16 páginas.
Esse total pode crescer quando um conto receber spreads adicionais; nesse caso o
mapa completo e o fechamento em cadernos devem ser recalculados antes da produção:

- 4 páginas iniciais;
- 7 capítulos com 8 páginas cada, totalizando 56 páginas narrativas;
- 4 páginas finais.

Cada capítulo começa em página ímpar e utiliza pelo menos quatro cenas:

1. uma ilustração vertical de abertura na página ímpar;
2. um panorama nas duas páginas seguintes;
3. um segundo panorama na página dupla seguinte;
4. um terceiro panorama na página dupla seguinte;
5. panoramas adicionais, quando aprovados pela extensão ou pelos momentos narrativos;
6. encerramento e reflexão na última página, em frente à abertura seguinte.

O Conto 1 é a referência de densidade desta obra: aproximadamente 631 palavras
narrativas distribuídas entre a abertura e três spreads. O revisor usa essa
relação com tolerância configurável para **avisar** quando um conto provavelmente
precisa de mais spreads. A decisão, os cortes textuais e o novo mapa de páginas
continuam editoriais; nada é criado ou removido silenciosamente.

O alerta `structure.illustration_plan.spread_density` informa a contagem narrativa,
o total planejado e o total sugerido. Ele não é autocorrigível: primeiro o editor
aprova a ampliação; depois o plano, a paginação, os prompts e as artes são atualizados.

O texto não é gerado dentro da imagem. Ele será composto pelo Layout sobre áreas de
baixo detalhe reservadas no prompt. Isso mantém a tipografia editável, evita letras
ilegíveis produzidas por modelos de imagem e permite ajustar corpo, entrelinha e
quebras sem regenerar a arte. Rostos, mãos, armas e símbolos importantes também ficam
fora da medianiz e das áreas de sangria.

O arquivo `plano_ilustracoes.yaml` contém as fichas de cena atualmente previstas. Cada ficha registra
função narrativa, âncora no manuscrito, descrição, personagens, continuidade,
texto alternativo, área destinada ao texto e caminho futuro do ativo. A bíblia visual
compartilhada acrescenta cinco disciplinas aos prompts:

- **ilustração:** guache e aquarela digital, acabamento editorial e legibilidade infantil;
- **fotografia virtual:** lente, altura de câmera, profundidade e foco narrativo;
- **cinematografia:** regra dos terços, linhas de condução, escala e leitura do spread;
- **cenografia:** arquitetura, roupas, objetos e materiais historicamente plausíveis;
- **cor e luz:** fonte de luz motivada, paleta e progressão emocional.

Os 28 prompts são compilados, sem gerar imagens, com:

```bash
python 2-edit/illustration_prompts.py \
  inputs/cronicas_chinesas_para_pequenos_guerreiros/plano_ilustracoes.yaml
```

O resultado `prompts_ilustracoes.md` traz um bloco copiável por cena, seu texto
alternativo e o destino reservado para o ativo futuro. Para mudar o estilo de todo o
livro, edita-se a bíblia visual uma vez e recompila-se o documento. Somente depois da
aprovação e produção das artes a fase deve mudar de `planejamento` para `producao`.

### Decisão arquitetural — separação do projeto de ilustração

O Ponto 5 permanece responsável por declarar **o que o livro precisa**: modo de
ilustração, número de cenas, páginas, âncoras textuais, continuidade, zonas de texto,
sangria e caminhos dos ativos. A geração e a aprovação das imagens não pertencem ao
motor de revisão textual. O projeto visual próprio
[`5-illustration`](../5-illustration/README.md) faz a conferência técnica das artes
aprovadas antes do envio ao Layout.

Pipeline visual contratado entre os projetos:

1. **brief e referências:** recebe o plano aprovado, a bíblia visual, personagens,
   cenários, objetos e âncoras do manuscrito;
2. **geração:** produz uma abertura e os spreads previstos, sem texto incorporado;
3. **revisão artística:** confere estilo, personagem, cenário, continuidade, emoção,
   movimento, câmera, luz, variedade entre cenas e ausência de artefatos;
4. **preflight técnico da imagem:** valida arquivo, formato, proporção, dimensões em
   pixels, resolução efetiva, perfil de cor, sangria, zona segura, medianiz, marcas,
   texto acidental e elementos importantes próximos ao corte;
5. **coerência imagem–texto:** compara cada arte com a âncora e o trecho que ela
   acompanha, verificando personagens, ação, objetos, momento da história, atmosfera,
   cronologia e espaço tipográfico;
6. **manifesto de aprovação:** somente ativos com estado `aprovada_para_layout`
   podem ser consumidos pelo projeto de diagramação;
7. **prova composta:** depois que o Layout aplicar o texto, uma nova revisão conjunta
   confere leitura, contraste, recorte, sangria, medianiz e coerência entre página,
   texto e imagem.

Para o formato Pocket dos Contos Chineses, o preflight deve considerar as dimensões
**já com 3 mm de sangria**: abertura de 131 × 186 mm (1547 × 2197 px a 300 dpi) e
spread de 256 × 186 mm (3024 × 2197 px a 300 dpi). Alterar somente o metadado de dpi
não é suficiente; a quantidade real de pixels deve atender ao suporte final.

O preflight técnico já está implementado. Seu modo padrão apenas avisa e produz um
relatório; nenhuma correção ocorre sem `--apply --confirm-fixes`. Revisão artística,
coerência imagem–texto e prova composta continuam como portões editoriais humanos.

## Ponto 7 — legibilidade

Status: **implementado como linha de base; validação final adiada até os pontos 1–6**.

A análise de legibilidade oferece:

- pontuação global;
- pontuação por capítulo ou conto;
- pontuação por seção, incluindo reflexões;
- comparação entre narração, diálogo e reflexão;
- frases acima do limite configurado;
- vocabulário potencialmente difícil por tamanho e sílabas estimadas;
- trechos locais com menor pontuação;
- achados com linha, capítulo e sugestão;
- metas diferentes para cada livro.

Exemplo de configuração:

```yaml
faixa_etaria: "8 anos"

revisao:
  legibilidade:
    min_flesch: 75
    max_palavras_frase: 24
    silabas_palavra_dificil: 4
    min_letras_palavra_dificil: 8
    max_itens_relatorio: 10
    min_palavras_secao: 40
    ignorar_palavras:
      - imperador
      - general
```

Interpretação dos campos:

- `min_flesch`: meta editorial global e por seção.
- `max_palavras_frase`: limite de triagem para leitura em voz alta.
- `silabas_palavra_dificil`: número estimado a partir do qual uma palavra é listada.
- `min_letras_palavra_dificil`: evita listar palavras curtas com encontros vocálicos.
- `max_itens_relatorio`: limita listas de exemplos, sem esconder a contagem total.
- `min_palavras_secao`: evita classificar blocos pequenos com amostra insuficiente.
- `ignorar_palavras`: vocabulário temático conhecido que não deve gerar ruído.

Uma seção abaixo da meta recebe `observacao`, não `erro`. Uma frase longa pode
ter ritmo deliberado; uma palavra longa pode ser compreensível pelo contexto.

## Roteiro dos 20 pontos

O desenvolvimento é sequencial. Cada ponto deve ser implementado, testado e validado
editorialmente antes do início do seguinte.

| # | Ponto | Estado atual |
|---:|---|---|
| 1 | Gramática e correção linguística | Validado editorialmente |
| 2 | Coesão e conexão de ideias | Validado editorialmente |
| 3 | Coerência e continuidade interna | Validado editorialmente |
| 4 | Factualidade, fontes, anacronismos e sustentação | Validado editorialmente |
| 5 | Estrutura conforme o framework do livro | Arquitetura validada; produção e revisão visual delegadas ao futuro `5-illustration` |
| 6 | Ponto de vista e voz narrativa | Validado editorialmente |
| 7 | Legibilidade global e local | Implementado como linha de base |
| 8 | Adequação etária linguística e temática | Pendente |
| 9 | Folha de estilo ampliada | Parcial: grafia e termos proibidos |
| 10 | Palavras-muleta, intensificadores e redundâncias | Parcial: lista e contagem global |
| 11 | Repetições e ecos locais | Parcial: frequência global |
| 12 | Prosa formulaica | Base implementada |
| 13 | Clichês, metáforas e imagens desgastadas | Pendente |
| 14 | Ritmo e proporção | Pendente |
| 15 | Tipografia e mecânica dos diálogos | Parcial: normalizações seguras |
| 16 | Função e naturalidade dos diálogos | Pendente |
| 17 | Equilíbrio entre mostrar, contar e explicar | Pendente |
| 18 | Sensibilidade cultural e representação | Pendente |
| 19 | Coerência entre proposta, história e reflexão | Pendente |
| 20 | Prova final e integridade editorial | Parcial: comparação e preservação |

## Entregáveis

- `outputs/<livro>/relatorios/relatorio_revisao.md`: relatório para leitura humana.
- `outputs/<livro>/relatorios/achados_revisao.json`: dados estruturados e métricas.
- `outputs/<livro>/relatorios/comparacao_original_revisado.md`: diferenças entre versões.
- `inputs/<livro>/texto_revisado.md`: manuscrito ativo.
- `inputs/<livro>/revisions/`: revisões datadas.
- `inputs/<livro>/revisions/backups/`: versões preservadas antes de escrita.

## Testes

```bash
python -m unittest discover -s 2-edit/tests -v
```

Os testes cobrem atualmente:

- ortografia determinística e preservação de maiúsculas;
- concordância impessoal, regência, crase e pronomes;
- duplicações, pontuação e balanceamento de delimitadores;
- exceções configuráveis e falsos positivos gramaticais;
- conectores redundantes, correlativos e repetidos;
- entidades, aposições e ambiguidades pronominais;
- distinção entre referência narrativa e fala;
- estados terminais e reutilização incompatível de personagens ou objetos;
- ordem de marcos narrativos e consistência de fatos numéricos;
- cobertura observável das regras de continuidade configuradas;
- alegações sustentadas, sem fonte, imprecisas e com referências inválidas;
- anacronismos narrativos e exceções em reflexões modernas;
- ausência de requisitos universais quando nenhuma estrutura é configurada;
- registro e ordem de capítulos, seções configuráveis e hierarquia Markdown;
- imagens sem texto alternativo, arquivos de mídia ausentes e proporções estruturais específicas por livro;
- falsos positivos de prosa formulaica;
- densidade dos marcadores;
- segmentação de legibilidade;
- separação entre narração, diálogo e reflexão;
- metas configuráveis;
- frases longas e vocabulário potencialmente difícil;
- IDs e localização dos achados;
- backup antes de escrita;
- criação de versão sem alteração do manuscrito ativo.

## Limitações atuais

- A revisão gramatical não possui dicionário abrangente nem análise sintática.
- As regras gramaticais privilegiam precisão e baixa incidência de falsos positivos,
  portanto não cobrem todos os desvios possíveis.
- A separação silábica é estimada por grupos vocálicos.
- A classificação de uma linha iniciada por travessão considera a linha inteira como diálogo.
- Vocabulário difícil é identificado por forma, não por familiaridade real do leitor.
- Flesch não avalia tema, emoção, conhecimento prévio ou qualidade literária.
- Os pontos 6 a 20 ainda precisam de implementação ou aprofundamento, exceto pelas
  bases já indicadas no roteiro.
