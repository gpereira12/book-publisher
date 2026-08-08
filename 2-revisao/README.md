# 📝 Projeto 2: Revisão — Engine de Qualidade & Lapidação Editorial

Este projeto é o motor de controle de qualidade do **Hub Editorial**. Ele recebe o manuscrito bruto do **Projeto 1 (Escrita)** e o passa por **5 Módulos de Revisão Editorial** antes de liberá-lo para a diagramação no **Projeto 3**.

---

## 🏛️ Os 5 Módulos de Revisão

1. **Revisão Estrutural & Coerência (`structural.py`)**: Valida se todos os capítulos possuem introdução, conflito e a seção de reflexão.
2. **Line Editing & Estilo (`style_dreyer.py`)**: Aplica o expurgo de palavras muleta (Dreyer), detecta termos repetidos e calcula a meta dos 10% de corte (Stephen King).
3. **Sanitização Tipográfica & Folha de Estilo (`typography.py`)**: Converte hífens em travessões (`—`), aspas inglesas em inteligentes (`“”`) e aplica as regras da folha de estilo (`style_sheet.yaml`).
4. **Legibilidade & Adequação Etária (`flesch_readability.py`)**: Calcula a pontuação de legibilidade Flesch-Siqueira adaptada para o Português (pt-BR).
5. **Checagem de Anacronismos**: Alerta para inconsistências de termos de época.

---

## 🚀 Como Executar

```bash
# Executar a revisão completa de um livro:
python 2-revisao/main.py --book-dir cronicas_chinesas_para_pequenos_guerreiros
```

---

## 📊 Entregáveis
* `reports/<livro>_revisao.md` — Relatório detalhado com pontuações, termos repetidos e alertas.
* `inputs/<livro>/texto_revisado.md` — Manuscrito lapidado e pronto para o Projeto 3.
