---
description: Design de capas profissionais (Horizontal, Miolo e IA).
---

# Workflow: Capa (/capa)

Este workflow foca exclusivamente na identidade visual externa do livro.

## Operação do Agente

1. **Coleta de Dimensões:**
   - Pergunte sobre as orelhas (se existem e tamanho).
   - Calcule a lombada baseada no número de páginas (fornecido pelo usuário ou lido do arquivo).

2. **Criação de Arte:**
   - Sugira conceitos visuais.
   - Gere a imagem de fundo via `generate_image`.

3. **Posicionamento:**
   - Organize os textos (Título, Autor, Sinopse na contracapa).
   - Gere o `capa_horizontal.pdf` com 10mm de sangria e marcas de registro.

---
**Comando de atalho:** `/capa`
