
#set page(
  width: 273.0mm,
  height: 200.0mm,
  margin: 0pt,
  fill: rgb("#1c1817")
)

#set text(font: "Georgia", fill: rgb("ffffff"), lang: "pt")
#let gold = rgb("#8c6d1f")

#box(width: 100%, height: 100%)[
  #stack(dir: ltr,
    // 1. Sangria Esquerda
    rect(width: 10.0mm, height: 100%, fill: rgb("#1c1817")),

    // 2. Contracapa Minimalista
    rect(width: 125.0mm, height: 100%, fill: rgb("#1c1817"), inset: 20pt)[
      #v(2cm)
      #align(center)[
        #text(size: 13pt, weight: "bold", fill: gold, tracking: 1.5pt)[CRÔNICAS CHINESAS PARA PEQUENOS GUERREIROS]
        #v(0.4cm)
        #line(length: 40pt, stroke: 0.8pt + gold)
      ]

      #v(1cm)
      #rect(width: 100%, fill: rgb("1c191c"), radius: 4pt, inset: 14pt, stroke: 0.5pt + rgb("2a262a"))[
        #set par(leading: 0.7em)
        #text(size: 9.5pt, fill: rgb("e2e2e2"))[Sinopse do livro aqui.]
      ]

      #v(1fr)
      #grid(
        columns: (1fr, auto),
        align: (left + horizon, right + horizon),
        image("../../resources/logos/coala/logo.svg", width: 65pt),
        image("assets/isbn_barcode.svg", width: 105pt)
      )
    ],

    // 3. Lombada
    rect(width: 3.0mm, height: 100%, fill: rgb("0e0d0f"), inset: 0pt)[
      #place(center + horizon)[
        #rotate(-90deg)[
          #block(width: 160.0mm)[
            #align(center)[
              #text(size: 7.5pt, weight: "bold", fill: gold, tracking: 1pt)[CRÔNICAS CHINESAS PARA PEQUENOS GUERREIROS • GABRIEL PEREIRA]
            ]
          ]
        ]
      ]
    ],

    // 4. Capa Frontal - Preset Tipográfico Minimalista
    rect(width: 135.0mm, height: 100%, fill: rgb("#1c1817"), inset: 25pt)[
      #v(2.5cm)
      #align(center)[
        #rect(stroke: 1.5pt + gold, radius: 4pt, inset: 20pt)[
          #v(0.5cm)
          #text(size: 20pt, weight: "bold", fill: gold, tracking: 1.5pt)[CRÔNICAS CHINESAS PARA PEQUENOS GUERREIROS]
          #v(10pt)
          #line(length: 50pt, stroke: 1pt + gold)
          #v(10pt)
          #text(size: 9pt, style: "italic", fill: rgb("f0e6d2"))[Histórias Milenares de Coragem, Sabedoria e Autocontrole]
          #v(0.5cm)
        ]

        #v(3cm)
        #text(size: 11pt, weight: "bold", tracking: 2.5pt)[GABRIEL PEREIRA]
      ]
    ]
  )
]
