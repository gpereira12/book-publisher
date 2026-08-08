# ✍️ Projeto 1: Escrita — O Motor de Criação & Geração do Hub Editorial

Este projeto é responsável por transformar uma ideia ou briefing bruto em um manuscrito completo em **Markdown padronizado** com metadados em **YAML Frontmatter**, pronto para os pipelines de Revisão (Projeto 2) e Diagramação (Projeto 3).

---

## 🏛️ Frameworks Narrativos Suportados

| Id do Framework | Gênero Indicado | Descrição Breve |
| :--- | :--- | :--- |
| `brooks_story_engineering` | Ficção / Suspense / Drama | Estrutura de 4 Partes (25% cada) com Pinch Points (37.5% e 62.5%) e Midpoint. |
| `snowflake` | Fantasia / Ficção Épica | Método Floco de Neve (Frase → Parágrafo → Personagens → Cenas). |
| `save_the_cat` | Ficção Rápida / Aventura | 15 Batidas Narrativas com porcentagens estritas. |
| `minto_pyramid` | Não-Ficção / Negócios | Pirâmide de Minto: Situação → Complicação → Tese Direta. |
| `scholastic_aquinas` | Teologia / Filosofia | Método Escolástico: Questão → Objeções → Sed Contra → Resposta. |
| `devotional_n_days` | Espiritualidade / Práticas | Jornada em N Dias: Texto → Reflexão → Aplicação → Oração. |
| `kishotenketsu` | Mangás / Slice of Life | 4 Atos Orientais sem dependência de conflito violento. |

---

## 🚀 Como Usar

```bash
# Execução interativa para criar um novo livro:
python main.py

# Execução direta por arquivo de configuração:
python main.py --config book_config.yaml
```
