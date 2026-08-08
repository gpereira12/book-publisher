# 🎨 Projeto 4: Capas & Artes — Cover & Asset Generation Engine

Este projeto é o motor de geração de capas gráficas e artes do **Hub Editorial**. Ele lê o número exato de páginas gerado pelo **Projeto 3 (Diagramação)** e constrói a **Capa Horizontal Aberta Completa** para gráfica em PDF (CMYK / 300 DPI).

---

## 🏛️ Funcionalidades

1. **Cálculo Matemático da Lombada (`spine_calculator.py`)**: Calcula a espessura da lombada baseando-se na contagem real de páginas do PDF e no tipo de papel.
2. **Suporte a Brochura & Capa Dura**:
   - *Brochura:* Inclui Orelhas de 70mm e sangria de 10mm.
   - *Capa Dura:* Inclui Vira de 35mm e Calhas de 10mm.
3. **Compilação via Typst (`cover_base.typ`)**: Gera o PDF vetorial em `outputs/<livro>/capas/capa_horizontal_grafica.pdf`.

---

## 🚀 Como Executar

```bash
python 4-capas/main.py --book-dir cronicas_chinesas_para_pequenos_guerreiros
```
