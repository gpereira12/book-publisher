# Projeto 5 — Ilustrações

Motor de conferência e preparação das artes antes da diagramação. Ele não gera
imagens e não substitui a aprovação artística.

O comando padrão é somente diagnóstico: lê `plano_ilustracoes.yaml`, mede os pixels
reais, calcula a resolução efetiva no suporte com sangria, compara extensão e formato,
confere perfil ICC, proporção e possível linha artificial na medianiz. O relatório é
salvo em `outputs/<livro>/illustrations/preflight.json`.

```bash
python3 5-illustration/main.py \
  --book-dir cronicas_chinesas_para_pequenos_guerreiros \
  --chapter 2
```

Nenhum arquivo é alterado nessa etapa. Depois de revisar os avisos, a correção é
explicitamente autorizada com as duas opções abaixo:

```bash
python3 5-illustration/main.py \
  --book-dir cronicas_chinesas_para_pequenos_guerreiros \
  --chapter 2 \
  --apply --confirm-fixes
```

Antes de escrever, o motor copia cada fonte para
`assets/interior/originais/conto_NN/`. As saídas são PNG RGB com perfil sRGB,
metadado de 300 dpi e dimensões exatas declaradas no plano. Ampliação e redução usam
Lanczos; o pequeno reenquadramento necessário é centralizado.

Se o arquivo final ainda não existe ou a fonte tem outra extensão, a cena pode
declarar `preflight.source_file`. O motor lê e preserva essa fonte e grava o destino
indicado em `arquivo`. Nas conferências seguintes, passa a validar o destino final.

A remoção da linha central nunca é presumida apenas pelo detector: além do aviso, a
cena precisa declarar `preflight.remove_center_seam: true` no manifesto. Isso evita
apagar por engano uma coluna, porta ou outro elemento arquitetônico legítimo.
