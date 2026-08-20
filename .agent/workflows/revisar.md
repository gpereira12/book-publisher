---
description: Revisão editorial de textos (Alinhamento, Estilo, Estrutura, Gramatical).
---

# Workflow: Revisar (/revisar)

Este workflow foca exclusivamente no aprimoramento textual e auditoria de prosa, sem acoplamento com artes ou diagramação.

## Arquitetura de Motores Desacoplados

1. **Motor de Revisão (2-edit):** Processa e valida puramente o manuscrito (Gramática, Estilo, Estrutura, Factualidade, Coesão e Coerência).
2. **Motor de Direção de Arte & Prompts (Futuro / Art Engine):** Consome o manuscrito revisado final para estruturar a bíblia visual e os prompts para o Google Flow (aplicando cinematografia, fotografia e ilustração).
3. **Motor de Diagramação & Prova (3-layout):** Consome o manuscrito revisado e as artes aprovadas para renderizar os PDFs/EPUBs finais.

## Operação do Agente de Revisão

1. **Escolha do Tipo de Revisão:**
   - Alinhamento (Tom e Voz).
   - Estilo (Pacing e Vocabulário).
   - Estrutura (Organização de capítulos).
   - Gramatical (Norma culta).
   - Factualidade & Coerência Narrative (Continuidades de longo alcance).
   - Final (Refino total).

2. **Briefing de Revisão:**
   - Confirmar o público-alvo, premissas de continuidade e nível de intervenção no `book_config.yaml`.

3. **Execução:**
   - Ler o `texto_original.md`.
   - Executar os módulos de auditoria do `2-edit`.
   - Salvar o resultado aprovado em `texto_revisado.md`.

4. **Feedback & Validação:**
   - Apresentar o relatório de achados para validação do usuário antes de prosseguir.

---
**Comando de atalho:** `/revisar`
