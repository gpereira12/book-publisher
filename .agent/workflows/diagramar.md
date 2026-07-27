---
description: Diagramação avançada de livros (Texto Pronto -> HTML -> PDFs Profissionais).
---

# Workflow: Diagramar (/diagramar)

Este workflow é ativado para diagramar livros que já possuem texto pronto (PDF ou MD). O processo é interativo e gera múltiplos entregáveis para gráfica e preview.

## Operação do Agente

1. **Briefing Inicial (Perguntas Sugestivas):**
   - Qual o caminho ou nome do livro na pasta `pendente/`?
   - Qual o formato desejado? (A5, A4, Pocket, Customizado)
   - Qual o Título e Autor para a folha de rosto?
   - Cor do papel: Branco ou Creme?
   - Capa: Deseja gerar uma imagem via IA ou usar um asset existente?

2. **Leitura e Preparação:**
   - Leia o arquivo em `pendente/` (MD ou PDF) **sem alterar o texto**.
   - Identifique capítulos e estrutura.
   - Execute o `scripts/content_splitter.py` para gerar a estrutura granular.

3. **Geração de Estética:**
   - Ative a skill `diagramador_estetica` para configurar margens áureas (ajustadas), fontes e headers.
   - Aplique o background com textura leve.
   - Renderize o `preview.html`.

4. **Produção de Entregáveis:**
   - Chame o motor de renderização ampliado para gerar:
     - `livro_completo.pdf` (Com capa).
     - `miolo_sangria.pdf` (Sem capa, com 3mm de sangria e marcas de corte).
     - `capa_horizontal.pdf` (Lombada, orelhas e 10mm de sangria).

5. **Notificação:**
   - Apresente os links para todos os arquivos na pasta `entregaveis/[Nome_do_Livro]/`.

---
**Comando de atalho:** `/diagramar`
