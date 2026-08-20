# Texturas de Fundo (Frente 2 do Cover v2)

Esta pasta está **vazia por padrão** — nenhuma textura real vem embutida no repositório (o motor de compositing não fabrica nem baixa imagens).

## Convenção

Coloque um arquivo `.jpg` por estilo tipográfico que você quiser suportar, nomeado com a mesma chave usada em `4-cover/design_engine/design_tokens.py` (`FONT_THEMES`):

```
resources/textures/imperial_oriental.jpg
resources/textures/romance_classico.jpg
resources/textures/infantojuvenil.jpg
resources/textures/academico_solene.jpg
resources/textures/misterio_thriller.jpg
resources/textures/poesia_contemporanea.jpg
resources/textures/geek_scifi.jpg
```

- Formato: JPG, RGB (sem transparência).
- Dimensões: pelo menos 2000×2000px. A textura e a ilustração recebem crop proporcional; nenhuma delas é esticada.
- Sugestão de conteúdo por estilo: papel de arroz/tinta nanquim (`imperial_oriental`), linho/textura de tecido (`romance_classico`), papel liso/aquarela clara (`infantojuvenil`, `poesia_contemporanea`), pergaminho/couro (`academico_solene`), concreto/metal escovado (`misterio_thriller`, `geek_scifi`).

## Como ativar

No `book_config.yaml` do livro:

```yaml
composicao_capa: true
textura_fundo: imperial_oriental   # opcional — senão deriva de estilo_tipografico
ilustracao_bruta: assets/illustration_raw.png   # opcional — default já é esse caminho
fade_direction: bottom   # "top" | "bottom" | "radial"
fade_start: 0.5
foco_x: 0.5   # enquadramento horizontal, de 0 a 1
foco_y: 0.5   # enquadramento vertical, de 0 a 1
```

Sem `composicao_capa: true`, nada muda — o Cover continua lendo `assets/capa.jpg` diretamente, como sempre fez.
