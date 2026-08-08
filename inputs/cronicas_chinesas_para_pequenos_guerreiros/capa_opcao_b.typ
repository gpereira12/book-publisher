
#set page(
  width: 273mm,
  height: 200mm,
  margin: 0pt,
  fill: rgb("#1c1817")
)

#set text(font: "Georgia", fill: rgb("ffffff"), lang: "pt")

#let gold = rgb("d4af37")

#box(width: 100%, height: 100%)[
  #stack(dir: ltr,
    // 1. Sangria Esquerda
    rect(width: 10mm, height: 100%, fill: rgb("#1c1817")),

    // 2. Contracapa Minimalista Homologada
    rect(width: 125mm, height: 100%, fill: rgb("141214"), inset: 20pt)[
      #v(2cm)
      #align(center)[
        #text(size: 14pt, weight: "bold", fill: gold, tracking: 1.5pt)[CRÔNICAS CHINESAS]
        #v(3pt)
        #text(size: 8.5pt, tracking: 2pt, fill: rgb("cccccc"))[PARA PEQUENOS GUERREIROS]
        #v(0.4cm)
        #line(length: 40pt, stroke: 0.8pt + gold)
      ]

      #v(1cm)
      #rect(width: 100%, fill: rgb("1c191c"), radius: 4pt, inset: 14pt, stroke: 0.5pt + rgb("2a262a"))[
        #set par(leading: 0.7em)
        #text(size: 9.5pt, fill: rgb("e2e2e2"))[Uma coletânea inesquecível de contos chineses tradicionais.]
      ]

      #v(1fr)
      #grid(
        columns: (1fr, auto),
        align: (left + horizon, right + horizon),
        image("../../resources/logos/coala/logo.svg", width: 65pt),
        image("../../inputs/cronicas_chinesas_para_pequenos_guerreiros/assets/isbn_barcode.svg", width: 105pt)
      )
    ],

    // 3. Lombada
    rect(width: 3.0mm, height: 100%, fill: rgb("0e0d0f"), inset: 0pt)[
      #place(center + horizon)[
        #rotate(-90deg)[
          #block(width: 160mm)[
            #align(center)[
              #text(size: 7.5pt, weight: "bold", fill: gold, tracking: 1pt)[CRÔNICAS CHINESAS • GABRIEL PEREIRA]
            ]
          ]
        ]
      ]
    ],

    // 4. Capa Frontal - Preset B1 Minimalista Homologado
    rect(width: 135mm, height: 100%, fill: rgb("141214"), inset: 25pt)[
      #v(3cm)
      #align(center)[
        #rect(stroke: 1.5pt + gold, radius: 4pt, inset: 20pt)[
          #v(0.5cm)
          #text(size: 22pt, weight: "bold", fill: gold, tracking: 1.5pt)[CRÔNICAS CHINESAS]
          #v(8pt)
          #text(size: 10pt, weight: "bold", fill: rgb("ffffff"), tracking: 2.5pt)[PARA PEQUENOS GUERREIROS]
          #v(10pt)
          #line(length: 50pt, stroke: 1pt + gold)
          #v(10pt)
          #text(size: 9pt, style: "italic", fill: rgb("f0e6d2"))[Histórias Milenares de Coragem, Sabedoria e Autocontrole]
          #v(0.5cm)
        ]

        #v(3.5cm)
        #text(size: 11pt, weight: "bold", tracking: 2.5pt)[GABRIEL PEREIRA]
      ]
    ]
  )
]
