/* ==============================================================================
   COMPONENTS.TYP - Antigravity Typst Layout Engine Components
   ==============================================================================
   Módulo de componentes para diagramação editorial avançada em Typst.
   Inclui: Molduras, Imagens Sangradas, Imagens Duplas (Spread), Divisores SVG e
   Balões de Mangá.
   ============================================================================== */

/// Renderiza um elemento (quadro, imagem ou texto) dentro de uma moldura estilizada.
/// - body: Conteúdo a ser emoldurado.
/// - border-color: Cor da borda da moldura (padrão: rgb("2c3e50")).
/// - thickness: Espessura da linha da moldura (padrão: 1.5pt).
/// - inset: Espaçamento interno entre a moldura e o conteúdo (padrão: 10pt).
/// - radius: Arredondamento dos cantos (padrão: 2pt).
#let moldura(
  body,
  border-color: rgb("#2c3e50"),
  thickness: 1.5pt,
  inset: 10pt,
  radius: 2pt
) = {
  block(
    width: 100%,
    stroke: thickness + border-color,
    inset: inset,
    radius: radius,
    body
  )
}

/// Renderiza uma imagem ocupando 100% da área da página, extrapolando as margens e sangria.
/// - image-path: Caminho ou objeto de imagem.
/// - alt-text: Texto alternativo/acessibilidade.
#let full-bleed(image-path, alt-text: "") = {
  place(
    top + left,
    dx: -0.5in - 5mm, // compensa margens e bleed na página
    dy: -0.5in - 5mm,
    block(
      width: 100% + 1in + 10mm,
      height: 100% + 1in + 10mm,
      image(image-path, width: 100%, height: 100%, fit: "cover")
    )
  )
}

/// Renderiza uma imagem expansiva para página dupla (spread de 2 páginas).
/// - image-path: Caminho ou objeto da imagem de alta resolução.
/// - page-side: "left" ou "right" para indicar qual metade renderizar.
#let double-spread(image-path, page-side: "left") = {
  // Configuração para ocupação total da lâmina
  let x-align = if page-side == "left" { right } else { left }
  place(
    top + left,
    dx: -0.5in - 5mm,
    dy: -0.5in - 5mm,
    block(
      width: 200% + 2in + 20mm,
      height: 100% + 1in + 10mm,
      clip: true,
      align(x-align, image(image-path, height: 100%, fit: "cover"))
    )
  )
}

/// Cria uma abertura de capítulo ilustrada em página ímpar.
/// O texto permanece tipograficamente editável e a transição para a imagem é
/// produzida pelo motor de diagramação, sem precisar ser incorporada à arte.
/// - title: Título do capítulo.
/// - opening-text: Trecho inicial exibido na abertura.
/// - image-path: Arte vertical aprovada para a abertura.
/// - chapter-label: Rótulo curto, como "Conto 1".
/// - attribution: Crédito ou nota de origem opcional.
/// - page-width/page-height: Formato físico da página.
/// - image-height: Altura ocupada pela imagem a partir da base.
/// - fade-height: Altura da transição suave entre papel e imagem.
#let illustrated-chapter-opener(
  title,
  opening-text,
  image-path,
  chapter-label: none,
  attribution: none,
  page-width: 125mm,
  page-height: 180mm,
  paper-color: rgb("#fdf5e6"),
  text-color: rgb("#25231f"),
  image-height: 118mm,
  fade-height: 30mm,
) = {
  pagebreak(weak: true, to: "odd")
  page(
    width: page-width,
    height: page-height,
    margin: 0mm,
    fill: paper-color,
    header: none,
    footer: none,
  )[
    #place(bottom + left)[
      #block(width: page-width, height: image-height, clip: true)[
        #image(
          image-path,
          width: page-width,
          height: image-height,
          fit: "cover",
          position: center + bottom,
        )
        #place(top + left)[
          #rect(
            width: page-width,
            height: fade-height,
            stroke: none,
            fill: gradient.linear(
              paper-color,
              paper-color.transparentize(100%),
              angle: 90deg,
            ),
          )
        ]
      ]
    ]

    #place(top + left, dx: 16mm, dy: 16mm)[
      #block(width: page-width - 32mm)[
        #if chapter-label != none [
          #text(
            size: 7.5pt,
            weight: "semibold",
            tracking: 1.2pt,
            fill: text-color.lighten(28%),
            smallcaps(chapter-label),
          )
          #v(4mm)
        ]
        #text(
          size: 20pt,
          weight: "bold",
          font: "Georgia",
          fill: text-color,
          tracking: -0.15pt,
          title,
        )
        #v(4.5mm)
        #if attribution != none [
          #text(
            size: 7.3pt,
            style: "italic",
            fill: text-color.lighten(24%),
            attribution,
          )
          #v(4.5mm)
        ]
        #set par(justify: true, leading: 0.75em, first-line-indent: 0em, spacing: 1.2em)
        #text(size: 9.2pt, fill: text-color, opening-text)
      ]
    ]
  ]
}

/// Insere um divisor decorativo SVG centralizado no fluxo de texto.
/// - svg-content: Caminho da imagem SVG ou string SVG.
/// - width: Largura do divisor (padrão: 40%).
#let svg-divider(svg-content, width: 40%) = {
  align(center, block(
    width: width,
    margin: (top: 1.5em, bottom: 1.5em),
    image(svg-content, width: 100%)
  ))
}

/// Balão de fala ou pensamento para Mangás / HQs.
/// - content: Texto dentro do balão.
/// - type: "speech" (fala normal), "thought" (pensamento), ou "scream" (grito/ação).
/// - bg: Cor de fundo (padrão: branco).
#let manga-balloon(content, type: "speech", bg: rgb("#ffffff")) = {
  let stroke-style = 1.5pt + black
  let radius = if type == "thought" { 15pt } else if type == "scream" { 0pt } else { 8pt }
  
  block(
    fill: bg,
    stroke: stroke-style,
    inset: 12pt,
    radius: radius,
    align(center + horizon, text(size: 10pt, font: "Liberation Serif", content))
  )
}
