/* ==============================================================================
   ROMANCE.TYP - Preset para Edições de Literatura / Romance
   ==============================================================================
   Estilização elegante para cabeçalhos de capítulos, capitulares (drop caps),
   epígrafes e alinhamento tipográfico clássico.
   ============================================================================== */

#import "book_base.typ": book-base
#import "components.typ": moldura, full-bleed, double-spread, svg-divider, illustrated-chapter-opener

#let romance-theme(
  title: "Título do Romance",
  subtitle: none,
  author: "Nome do Autor",
  isbn: "978-0-00000-000-0",
  publisher: "Editora Boutique",
  year: "2026",
  format: "A5",
  acabamento: "brochura",
  paper-color: rgb("fdf5e6"),
  body
) = {
  // Customização de Títulos de Capítulos (Heading 1)
  show heading.where(level: 1): it => {
    pagebreak(weak: true, to: "odd")
    v(3cm)
    align(center)[
      #text(size: 11pt, font: "Georgia", style: "italic", fill: luma(80), "Capítulo")
      #v(0.5cm)
      #text(size: 20pt, weight: "bold", font: "Georgia", it.body)
      #v(1.5cm)
    ]
  }

  // Estilização de Citações / Epígrafes
  show quote: it => {
    align(right)[
      #block(
        width: 75%,
        inset: (left: 10pt),
        text(size: 9.5pt, style: "italic", fill: luma(60), it.body)
      )
    ]
  }

  book-base(
    title: title,
    subtitle: subtitle,
    author: author,
    isbn: isbn,
    publisher: publisher,
    year: year,
    format: format,
    acabamento: acabamento,
    paper-color: paper-color,
    golden-margins: true,
    body
  )
}
