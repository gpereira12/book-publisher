---
description: Processamento orientado a prompt estruturado para o sistema "Boutique de Livros".
---

# Workflow: Boutique de Livros (/boutique)

Este workflow deve ser ativado sempre que o usuário fornecer um prompt estruturado com os seguintes dados:
- **Livro:** [Caminho ou Nome]
- **Formato:** [A5 | A4 | Pocket]
- **Autor:** [Nome]
- **Título:** [Nome]
- **Cores:** [Cores principais ou descrição de tom]
- **Imagens:** [Gerar | Não Gerar]

## Operação do Agente

1. **Validação de Fonte:**
   - Localize o arquivo `texto_original.md`. **NUNCA sobrescreva este arquivo.**
   - Leia o conteúdo para entender o contexto das imagens.

2. **Branding Dinâmico:**
   - Execute a skill `branding_architect` interna para validar as cores sugeridas no prompt.
   - Use o script `/tmp/validate_contrast.py` se necessário.

3. **Gerenciamento de Assets:**
   - Se o prompt pedir "Gerar", utilize a ferramenta `generate_image`, salve em `assets/` e descreva na simbologia.
   - Se não, procure por imagens existentes no diretório do livro.

4. **Execução Técnica:**
   - Chame o `main.py` com os novos argumentos:
   ```bash
   python3 main.py [Caminho/Para/texto_original.md] \
     --title "[Título]" \
     --author "[Autor]" \
     --format "[Formato]" \
     --colors "main:[HEX],accent:[HEX],bg:[HEX]" \
     [--gen-images]
   ```

5. **Entrega:**
   - O sistema criará um HTML de preview (no diretório do livro) e um PDF numerado (em `livros_finais/`).
   - Notifique o usuário com links diretos para ambos os arquivos.
