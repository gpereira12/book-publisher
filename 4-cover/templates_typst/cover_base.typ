/* ==============================================================================
   COVER_BASE.TYP - Absolute Canvas Engine (Professional Commercial Standard)
   ==============================================================================
   Motor de capas gráficas baseado em coordenadas de canvas absoluto (Layered Grid):
   - Elimina tiras verticais artificiais (Bleed integrado 100% ao fundo).
   - Capa Frontal Full-Bleed Real: Imagem preenche 100% da altura e largura da capa.
   - Camadas Z-Index: 0: Canvas Base | 1: Arte Full-Bleed | 2: Sombras | 3: Tipografia Ouro.
   ============================================================================== */

#let get-page-dimensions(format) = {
  if format == "A5" { (148mm, 210mm) }
  else if format == "14x21" { (140mm, 210mm) }
  else if format == "Pocket" { (125mm, 180mm) }
  else if format == "Trade" { (152mm, 228mm) }
  else { (148mm, 210mm) }
}

#let make-cover(
  title: "Crônicas Chinesas para Pequenos Guerreiros",
  subtitle: "Histórias Milenares de Coragem, Sabedoria e Autocontrole",
  author: "Gabriel Pereira",
  publisher: "Editora Coala",
  isbn: "978-65-988202-7-5",
  synopsis: "Uma coletânea inesquecível de contos chineses tradicionais que ensinam virtudes como resiliência, autocontrole, paciência e coragem para a nova geração de guerreiros.",
  author_bio: "Gabriel Pereira é autor e apaixonado pela literatura e sabedoria oriental.",
  format: "Pocket",
  acabamento: "brochura", // brochura | capadura | grampo | espiral
  orelha_mm: 0,           // 0mm para Livro de Bolso sem orelhas
  spine_mm: 3.0,
  bg_color: rgb("121113"),
  cover_image: none,
  logo_image: none,
  barcode_image: none
) = {
  let dims = get-page-dimensions(format)
  let page-w = dims.at(0)
  let page-h = dims.at(1)

  // Orelhas e Vira
  let flap-w = if acabamento == "capadura" { 35mm } else if acabamento == "brochura" { orelha_mm * 1mm } else { 0mm }
  let is-hardcover = (acabamento == "capadura")
  
  // Calhas e Espiral
  let hinge-w = if is-hardcover { 10mm } else { 0mm }
  let spiral-w = if acabamento == "espiral" { 8mm } else { 0mm }

  // Sangria externa
  let bleed = if is-hardcover { 0mm } else if acabamento in ("grampo", "espiral") { 5mm } else { 10mm }

  // Lombada
  let actual-spine = if acabamento in ("grampo", "espiral") { 0mm } else { spine_mm * 1mm }

  // Largura e Altura Totais do Canvas
  let total-w = (bleed * 2) + (flap-w * 2) + (page-w * 2) + (hinge-w * 2) + (spiral-w * 2) + actual-spine
  let total-h = (bleed * 2) + page-h

  set page(
    width: total-w,
    height: total-h,
    margin: 0pt,
    fill: bg_color
  )

  set text(font: "Georgia", fill: rgb("ffffff"), lang: "pt")

  let gold-color = rgb("d4af37")
  let soft-gold = rgb("f0e6d2")
  let dark-bg = rgb("121113")

  // X Positions para Posicionamento Absoluto
  let x-back-cover = bleed + flap-w
  let x-spine = x-back-cover + page-w + hinge-w
  let x-front-cover = x-spine + actual-spine + hinge-w + spiral-w

  box(width: total-w, height: total-h)[
    // =========================================================================
    // 1. CONTRACAPA (QUARTA CAPA) - Posicionamento Preciso
    // =========================================================================
    #place(top + left, dx: x-back-cover, dy: bleed)[
      #rect(width: page-w, height: page-h, fill: dark-bg, inset: 20pt)[
        #v(1cm)
        #align(center)[
          #text(size: 13pt, weight: "bold", tracking: 1.5pt, fill: gold-color)[CRÔNICAS CHINESAS]
          #v(3pt)
          #text(size: 8.5pt, tracking: 2pt, fill: rgb("cccccc"))[PARA PEQUENOS GUERREIROS]
          #v(0.4cm)
          #line(length: 40pt, stroke: 0.8pt + gold-color)
        ]

        #v(0.8cm)
        #rect(width: 100%, fill: rgb("1a181a"), radius: 4pt, inset: 14pt, stroke: 0.5pt + rgb("2c282c"))[
          #set par(leading: 0.7em)
          #text(size: 9.5pt, fill: rgb("e2e2e2"))[#synopsis]
        ]

        #v(1fr)
        #grid(
          columns: (1fr, auto),
          align: (left + horizon, right + horizon),
          if logo_image != none [
            #image(logo_image, width: 65pt)
          ] else [
            #text(size: 10pt, weight: "bold", fill: gold-color)[#publisher]
          ],
          if barcode_image != none [
            #image(barcode_image, width: 105pt)
          ] else [
            #rect(width: 100pt, height: 45pt, fill: rgb("ffffff"), radius: 2pt, inset: 4pt)[
              #align(center + horizon)[
                #text(size: 7pt, fill: rgb("000000"))[ISBN #isbn]
              ]
            ]
          ]
        )
      ]
    ]

    // =========================================================================
    // 2. LOMBADA - Texto Monolinha em Ouro
    // =========================================================================
    #if actual-spine > 0mm [
      #place(top + left, dx: x-spine, dy: bleed)[
        #rect(width: actual-spine, height: page-h, fill: rgb("0b0a0c"), inset: 0pt)[
          #place(center + horizon)[
            #rotate(-90deg)[
              #block(width: page-h - 2cm)[
                #align(center)[
                  #text(
                    size: if spine_mm < 4.0 { 6.5pt } else if spine_mm < 7.0 { 8.5pt } else { 10.5pt },
                    weight: "bold",
                    fill: gold-color,
                    tracking: 1pt
                  )[#title.replace(" para Pequenos Guerreiros", "") • #author]
                ]
              ]
            ]
          ]
        ]
      ]
    ]

    // =========================================================================
    // 3. CAPA FRONTAL - Full-Bleed 100% Real (Sem Caixinha e Sem Tiras de Borda)
    // =========================================================================
    #place(top + left, dx: x-front-cover, dy: 0pt)[
      #box(width: page-w + bleed, height: total-h)[
        // CAMADA 1: Imagem Full-Bleed preenchendo 100% da área útil + sangria
        #if cover_image != none [
          #place(top + left)[
            #image(cover_image, width: page-w + bleed, height: total-h, fit: "cover")
          ]
        ] else [
          #rect(width: 100%, height: 100%, fill: dark-bg)
        ]

        // CAMADA 2: Gradiente Superior para Leitura do Título
        #place(top + left)[
          #rect(
            width: 100%,
            height: 45%,
            fill: gradient.linear(dark-bg.darken(30%), dark-bg.transparentize(100%), dir: ttb),
            inset: (top: bleed + 20pt, left: 15pt, right: bleed + 15pt)
          )[
            #align(center)[
              #text(size: 21pt, weight: "bold", fill: gold-color, tracking: 1.5pt)[CRÔNICAS CHINESAS]
              #v(4pt)
              #text(size: 9.5pt, weight: "bold", fill: rgb("ffffff"), tracking: 2.5pt)[PARA PEQUENOS GUERREIROS]
              #v(6pt)
              #line(length: 35pt, stroke: 1pt + gold-color)
              #v(6pt)
              #if subtitle != none [
                #text(size: 8.5pt, style: "italic", fill: soft-gold)[#subtitle]
              ]
            ]
          ]
        ]

        // CAMADA 3: Gradiente Inferior para Leitura do Nome do Autor
        #place(bottom + left)[
          #rect(
            width: 100%,
            height: 25%,
            fill: gradient.linear(dark-bg.transparentize(100%), dark-bg.darken(30%), dir: ttb),
            inset: (bottom: bleed + 15pt, left: 15pt, right: bleed + 15pt)
          )[
            #align(center + bottom)[
              #text(size: 10.5pt, weight: "bold", fill: rgb("ffffff"), tracking: 2.5pt)[#upper(author)]
            ]
          ]
        ]
      ]
    ]

    // =========================================================================
    // 4. ORELHAS (Se Ativadas)
    // =========================================================================
    #if flap-w > 0mm [
      #place(top + left, dx: bleed, dy: bleed)[
        #rect(width: flap-w, height: page-h, fill: dark-bg.darken(15%), inset: 15pt)[
          #if not is-hardcover [
            #v(2cm)
            #text(size: 11pt, weight: "bold", fill: gold-color)[SOBRE O AUTOR]
            #v(0.3cm)
            #line(length: 25pt, stroke: 1pt + gold-color)
            #v(0.5cm)
            #set par(leading: 0.7em)
            #text(size: 9pt, fill: rgb("dddddd"))[#author_bio]
          ]
        ]
      ]
      
      #place(top + left, dx: x-front-cover + page-w, dy: bleed)[
        #rect(width: flap-w, height: page-h, fill: dark-bg.darken(15%), inset: 15pt)[
          #if not is-hardcover [
            #v(2cm)
            #if logo_image != none [
              #image(logo_image, width: 60pt)
              #v(0.3cm)
            ]
            #text(size: 11pt, weight: "bold", fill: gold-color)[#publisher]
            #v(0.5cm)
            #text(size: 9pt, fill: rgb("cccccc"))[Uma publicação oficial do selo #publisher.]
          ]
        ]
      ]
    ]
  ]
}
