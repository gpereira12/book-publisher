/* ==============================================================================
   APOSTILA.TYP - Preset para Livros de Atividades / Apostilas Infantis
   ==============================================================================
   Tipografia sem serifa, sem recuo de primeira linha, sem justificação — legível
   para o público infantil. Uma atividade por página, com título numerado e
   moldura de ilustração reaproveitando o componente `moldura` do motor.
   ============================================================================== */

#import "book_base.typ": book-base
#import "components.typ": moldura, full-bleed, double-spread, svg-divider, illustrated-chapter-opener

#let apostila-theme(
  title: "Título da Apostila",
  subtitle: none,
  author: "Nome do Autor",
  isbn: "978-0-00000-000-0",
  publisher: "Editora Boutique",
  year: "2026",
  format: "A4",
  acabamento: "brochura",
  paper-color: rgb("ffffff"),
  accent-color: rgb("#2c6e63"),
  body
) = {
  // Tipografia infantil: sem serifa, sem recuo, sem justificação.
  set text(
    font: "Helvetica",
    size: 13pt,
    fill: rgb("1a1a1a"),
    lang: "pt",
    region: "BR",
  )
  set par(justify: false, first-line-indent: 0pt, leading: 0.75em)

  // Cada atividade quebra para uma página nova, numerada e titulada.
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    v(2mm)
    text(size: 19pt, weight: "bold", it.body)
    v(5mm)
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
    golden-margins: false,
    body
  )
}

/// Renderiza uma atividade completa: título, fala opcional do mascote,
/// comando à criança e a ilustração (real ou placeholder) emoldurada.
/// - numero: número sequencial da atividade.
/// - titulo: título curto da atividade.
/// - comando: instrução dirigida à criança.
/// - imagem: caminho da imagem final (ou `none` se ainda não houver arte).
/// - carlinho: texto opcional do mascote, exibido acima do comando.
/// - accent-color: cor de destaque para a fala do mascote.
#let atividade(
  numero,
  titulo,
  comando,
  imagem: none,
  carlinho: none,
  accent-color: rgb("#2c6e63"),
) = {
  heading(level: 1)[Atividade #numero. #titulo]

  if carlinho != none {
    block(spacing: 6mm)[
      #text(size: 12pt, style: "italic", fill: accent-color, carlinho)
    ]
  }

  block(spacing: 8mm)[#text(size: 15pt, comando)]

  align(center)[
    #if imagem != none {
      moldura(
        image(imagem, width: 110mm),
        border-color: rgb("#dcdcdc"),
        thickness: 1pt,
        inset: 8pt,
        radius: 4pt,
      )
    } else {
      moldura(
        block(width: 110mm, height: 70mm, align(center + horizon)[
          #text(size: 11pt, fill: luma(150), style: "italic")[ilustração aquarelada — pendente de geração]
        ]),
        border-color: rgb("#dcdcdc"),
        thickness: 1pt,
        inset: 20mm,
        radius: 4pt,
      )
    }
  ]
}
