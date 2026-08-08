---
description: Produção e escrita iterativa de livros do zero com suporte aos 18 Frameworks Narrativos.
---

# Workflow: Escrever (/escrever) — Projeto 1 (Escrita)

Este workflow guia o autor no processo completo de concepção, estruturação e redação de um novo livro (Ficção, Não-Ficção, Teologia, Filosofia ou Mangá).

---

## Passo a Passo do Agente

### 1. Briefing & Conceituação (Interativo)
Faça perguntas diretas para entender a visão do autor:
- **Título ou Tema Central:** Sobre o que é o livro?
- **Gênero:** Ficção, Não-Ficção, Teologia/Filosofia, Espiritualidade ou Mangá/Novel?
- **Público & Tom:** Solene, Poético, Didático, Ágil ou Acadêmico?

### 2. Seleção de Framework & Camada de Estilo
Apresente a recomendação de **Framework Estrutural Principal** com base no gênero:
- 🏰 **Larry Brooks / Story Engineering** — Romances, Dramas e Suspenses (4 Partes / 25% / Pinch Points).
- ❄️ **Snowflake Method** — Fantasias e Ficção Científica (Construção progressiva).
- 📊 **Pirâmide de Minto** — Não-Ficção, Negócios e Manuais (Conclusão direta no topo).
- 📜 **Método Escolástico (Aquino)** — Teologia e Apologética (Questão → Objeções → Sed Contra → Resposta).
- 🙏 **Jornada em N Dias** — Devocionais e Espiritualidade Prática.
- 🌸 **Kishōtenketsu** — Mangás e Narrativas Orientais (4 Atos sem conflito direto).

*(Opcional: Oferecer a **Camada de Estilo de Autor**: Tolkien, Lewis, Chesterton, Rowling, Gotouge ou Yamada).*

### 3. Geração da Estrutura (`book_config.yaml` & Outline)
- Crie a pasta `inputs/[nome_do_livro]/`.
- Salve a configuração em `inputs/[nome_do_livro]/book_config.yaml`.
- Apresente o **Esboço de Capítulos (Outline)** detalhado para aprovação do autor.

### 4. Redação Iterativa Capítulo a Capítulo
- Redija **um capítulo por vez** com alta densidade literária (sem termos genéricos de IA, variando o tamanho das frases).
- Salve progressivamente em `inputs/[nome_do_livro]/texto_original.md` com YAML Frontmatter no topo.
- Ao fim de cada capítulo, peça feedback ao autor:
  - *`[Aprovar e Avançar]`*
  - *`[Refinar tom / Adicionar detalhes]`*

### 5. Finalização & Transição
Ao concluir o último capítulo, notifique que o manuscrito está pronto e ofereça a transição direta para o **Projeto 3 (Diagramação)** via comando `/diagramar`.

---
**Comando de atalho:** `/escrever`
