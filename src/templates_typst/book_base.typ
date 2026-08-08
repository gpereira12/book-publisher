/* ==============================================================================
   BOOK_BASE.TYP - Base Template & Layout Engine for Typst
   ==============================================================================
   Suporta formatos de página (A5, 14x21, Pocket, etc.), margens baseadas na Proporção
   Áurea (Golden Ratio), Sangria (Bleed 5mm), Acabamentos (Brochura, Capa Dura, Grampo, Espiral),
   Folha de Rosto, Ficha Catalográfica com contagem dinâmica de páginas e cabeçalhos espelhados.
   ============================================================================== */

#let get-page-size(format) = {
  if format == "A5" { (148mm, 210mm) }
  else if format == "14x21" { (140mm, 210mm) }
  else if format == "Pocket" { (125mm, 180mm) }
  else if format == "Trade" { (152mm, 228mm) }
  else if format == "A4" { (210mm, 297mm) }
  else { (148mm, 210mm) } // Default A5
}

#let get-binding-inside-margin(acabamento, is-golden) = {
  let base-inside = if is-golden { 20mm } else { 18mm }
  if acabamento == "espiral" { base-inside + 6mm }       // +6mm para furação do espiral / Wire-O
  else if acabamento == "capadura" { base-inside + 2mm }  // +2mm para dobra e calha de capa dura
  else if acabamento == "grampo" { base-inside - 2mm }    // -2mm grampo canoa (abre plano)
  else { base-inside }                                   // Brochura tradicional
}

#let book-base(
  title: "Título do Livro",
  subtitle: none,
  author: "Nome do Autor",
  isbn: "978-0-00000-000-0",
  publisher: "Editora Boutique",
  year: "2026",
  city: "São Paulo",
  format: "A5",
  acabamento: "brochura",
  bleed: 5mm,
  paper-color: rgb("fdf5e6"),
  golden-margins: true,
  body
) = {
  let size = get-page-size(format)
  let inside-margin = get-binding-inside-margin(acabamento, golden-margins)
  
  // Cálculo de Margens Áureas (Golden Ratio ~1.618) se ativado
  let margins = if golden-margins {
    (
      inside: inside-margin,
      outside: 12.3mm,
      top: 15mm,
      bottom: 24.3mm,
    )
  } else {
    (
      inside: inside-margin,
      outside: 15mm,
      top: 18mm,
      bottom: 20mm,
    )
  }

  // Configuração da Página Global (Com fundo 100% colorido)
  set page(
    paper: "a5",
    width: size.at(0),
    height: size.at(1),
    fill: paper-color,
    margin: margins,
    flipped: false,
    header: context {
      let page-num = counter(page).get().first()
      // Ocultar cabeçalho nas primeiras páginas (capa, folha de rosto, ficha)
      if page-num > 3 {
        if calc.even(page-num) {
          align(left, text(size: 9pt, fill: luma(100), font: "Georgia")[#author])
        } else {
          align(right, text(size: 9pt, fill: luma(100), font: "Georgia")[#title])
        }
      }
    },
    footer: context {
      let page-num = counter(page).get().first()
      if page-num > 3 {
        align(center, text(size: 10pt, weight: "medium")[#page-num])
      }
    }
  )

  // Configurações Globais de Parágrafo e Tipografia
  set text(
    font: "Georgia",
    size: 10.5pt,
    fill: rgb("1a1a1a"),
    lang: "pt",
    region: "BR",
    spacing: 120%,
    tracking: 0.2pt,
  )

  set par(
    justify: true,
    leading: 0.7em,
    first-line-indent: 1.5em,
  )

  // --- 1. FOLHA DE ROSTO ---
  page(header: none, footer: none)[
    #v(3cm)
    #align(center)[
      #text(size: 24pt, weight: "bold", tracking: 1pt)[#title]
      
      #if subtitle != none [
        #v(0.5cm)
        #text(size: 14pt, style: "italic", fill: luma(80))[#subtitle]
      ]

      #v(2cm)
      #text(size: 14pt, weight: "medium")[#author]

      #v(5cm)
      #text(size: 11pt, weight: "bold")[#publisher] \
      #text(size: 9pt, fill: luma(100))[#city, #year]
    ]
  ]

  // --- 2. FICHA CATALOGRÁFICA ---
  page(header: none, footer: none)[
    #v(8cm)
    #align(center)[
      #rect(
        width: 85%,
        stroke: 0.5pt + luma(120),
        inset: 12pt,
        radius: 2pt,
      )[
        #align(left)[
          #text(size: 8.5pt, font: "Courier")[
            Dados Internacionais de Catalogação na Publicação (CIP) \
            #line(length: 100%, stroke: 0.3pt + luma(150))
            
            #author. \
            #h(4pt) #title / #author. -- #city : #publisher, #year. \
            #h(4pt) #size.at(0) x #size.at(1) ; #format cm. \
            
            #h(4pt) Acabamento: #acabamento. \
            #h(4pt) ISBN #isbn \
            
            #h(4pt) 1. Literatura Infantojuvenil. 2. Contos. I. Título.
            
            #align(right)[CDD 808.83]
          ]
        ]
      ]
    ]
  ]

  // --- 3. CORPO DO LIVRO ---
  body
}
