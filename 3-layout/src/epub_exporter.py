#!/usr/bin/env python3
"""
src/epub_exporter.py
--------------------
Módulo exportador EPUB para a Boutique de Livros.
Gera arquivos .epub padrão OEBPS com metadados, estrutura de capítulos e folha de estilo.
Seguindo princípios de Clean Code/SOLID e baixa complexidade ciclomática.
"""

import os
import re
import sys
import uuid
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import markdown
import yaml

try:
    import ebooklib
    from ebooklib import epub
except ImportError:
    epub = None


def parse_markdown_content(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """Lê o arquivo Markdown e separa o YAML frontmatter do corpo de texto."""
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_yaml, body = parts[1], parts[2].strip()
    try:
        metadata = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        print(f"[Aviso] Erro ao ler YAML frontmatter: {exc}", file=sys.stderr)
        metadata = {}

    return metadata, body


def split_chapters(markdown_body: str) -> List[Tuple[str, str]]:
    """
    Divide o corpo do Markdown em capítulos baseados em cabeçalhos H1 (# ).
    Retorna uma lista de tuplas (titulo, conteudo_markdown).
    """
    lines = markdown_body.splitlines()
    chapters: List[Tuple[str, str]] = []
    current_title = "Introdução"
    current_lines: List[str] = []

    for line in lines:
        if line.startswith("# "):
            if current_lines:
                chapters.append((current_title, "\n".join(current_lines)))
                current_lines = []
            current_title = line[2:].strip()
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_lines:
        chapters.append((current_title, "\n".join(current_lines)))

    return chapters


def _create_epub_book(metadata: Dict[str, Any], config: Dict[str, Any]) -> Any:
    """Instancia o objeto EpubBook e configura seus metadados essenciais."""
    if epub is None:
        raise RuntimeError("A biblioteca 'ebooklib' não está instalada. Execute `pip install ebooklib`.")

    book = epub.EpubBook()

    title = config.get("title") or metadata.get("title", "Livro sem Título")
    author = config.get("author") or metadata.get("author", "Autor Desconhecido")
    language = metadata.get("language", "pt-BR")
    identifier = metadata.get("isbn") or str(uuid.uuid4())

    book.set_identifier(identifier)
    book.set_title(title)
    book.set_language(language)
    book.add_author(author)

    return book


def _get_epub_css() -> str:
    """Retorna o CSS embutido com padrão tipográfico refinado para leitores digitais."""
    return """
@namespace url("http://www.w3.org/1999/xhtml");

body {
    font-family: "Georgia", "Garamond", "Times New Roman", serif;
    line-height: 1.6;
    margin: 5%;
    padding: 0;
    text-align: justify;
}

h1, h2, h3, h4 {
    font-family: "Helvetica Neue", "Arial", sans-serif;
    font-weight: bold;
    text-align: center;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
}

h1 { font-size: 1.8em; }
h2 { font-size: 1.4em; }
h3 { font-size: 1.2em; }

p {
    text-indent: 1.5em;
    margin-top: 0;
    margin-bottom: 0;
}

p.first-para {
    text-indent: 0;
}

blockquote {
    font-style: italic;
    margin: 1.5em 2em;
    color: #444;
}

ul, ol {
    margin-left: 2em;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}
"""


def _build_chapter_item(index: int, title: str, md_content: str, style_item: Any) -> Any:
    """Converte o Markdown de um capítulo para HTML e constrói o objeto EpubHtml."""
    html_body = markdown.markdown(md_content, extensions=["tables", "sane_lists", "nl2br"])
    
    file_name = f"chap_{index:02d}.xhtml"
    chapter = epub.EpubHtml(
        title=title,
        file_name=file_name,
        lang="pt-BR"
    )
    
    chapter.content = f"<html><head></head><body>{html_body}</body></html>"
    chapter.add_item(style_item)
    return chapter


def _attach_cover_image(book: Any, cover_path_str: Optional[str]) -> None:
    """Associa a imagem de capa ao arquivo EPUB se existir."""
    if not cover_path_str:
        return
    cover_path = Path(cover_path_str)
    if cover_path.exists() and cover_path.is_file():
        try:
            with open(cover_path, "rb") as img_file:
                book.set_cover(cover_path.name, img_file.read())
            print(f"--> Capa anexada ao EPUB: {cover_path}")
        except Exception as exc:
            print(f"[Aviso] Erro ao anexar capa {cover_path}: {exc}", file=sys.stderr)


def export_epub(
    input_file: Path,
    output_file: Path,
    config: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Exporta um arquivo Markdown para .epub seguindo o fluxo de compilação Clean Code.
    """
    if config is None:
        config = {}

    try:
        metadata, md_body = parse_markdown_content(input_file)
        book = _create_epub_book(metadata, config)

        # Adicionar CSS
        style_css = _get_epub_css()
        css_item = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style_css
        )
        book.add_item(css_item)

        # Capa
        cover_image = config.get("cover_image") or metadata.get("cover")
        _attach_cover_image(book, cover_image)

        # Dividir e criar capítulos
        raw_chapters = split_chapters(md_body)
        epub_chapters = []

        for idx, (title, content) in enumerate(raw_chapters, start=1):
            chap_item = _build_chapter_item(idx, title, content, css_item)
            book.add_item(chap_item)
            epub_chapters.append(chap_item)

        # Tabela de Conteúdos (TOC) e Navegação
        book.toc = tuple(epub_chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Spine (Ordem de leitura)
        book.spine = ["nav"] + epub_chapters

        # Garantir diretório de saída
        output_file.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output_file), book, {})

        print(f"[Sucesso] Arquivo EPUB gerado com sucesso: {output_file}")
        return True

    except Exception as err:
        print(f"[Erro] Falha ao gerar EPUB: {err}", file=sys.stderr)
        return False


def build_parser() -> argparse.ArgumentParser:
    """Configura o parser CLI para execução independente do exportador EPUB."""
    parser = argparse.ArgumentParser(description="Boutique de Livros - EPUB Exporter")
    parser.add_argument("--input", "-i", required=True, help="Caminho do arquivo Markdown de entrada")
    parser.add_argument("--output", "-o", help="Caminho de saída para o arquivo .epub")
    parser.add_argument("--title", help="Título do livro (opcional)")
    parser.add_argument("--author", help="Autor do livro (opcional)")
    parser.add_argument("--cover", help="Caminho para imagem de capa (opcional)")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_epub = Path(args.output).resolve() if args.output else input_path.with_suffix(".epub")

    config = {
        "title": args.title,
        "author": args.author,
        "cover_image": args.cover
    }

    print(f"--> Exportando EPUB a partir de {input_path}...")
    success = export_epub(input_path, output_epub, config)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
