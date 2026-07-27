import os
import sys
import argparse
from src.parser import process_markdown
from src.builder import build_html
from src.pdf_printer import print_pdf

def get_input(prompt_text, default_value=""):
    """Função utilitária para pedir input interativo com valor padrão opcional."""
    if default_value:
        hint = f" [{default_value}]"
    else:
        hint = ""
    value = input(f"{prompt_text}{hint}: ").strip()
    return value if value else default_value

def main():
    print("========================================")
    print("      📚 BOUTIQUE DE LIVROS 3.0")
    print("========================================\n")

    parser = argparse.ArgumentParser(description="Diagramação Profissional de Livros")
    parser.add_argument("--book-dir", help="Nome da pasta do livro dentro de 'inputs/'")
    parser.add_argument("--format", help="Formato (A5, A4, Pocket)")
    parser.add_argument("--theme", help="Tema/Cor do Papel (Creme, Branco)")
    parser.add_argument("--author", help="Nome do Autor")
    parser.add_argument("--title", help="Título do Livro")
    parser.add_argument("--cover", help="Caminho da imagem de capa (deixe vazio para gerar com IA)")
    parser.add_argument("--digital-only", action="store_true", help="Gerar apenas a versão digital")
    parser.add_argument("--print-only", action="store_true", help="Gerar apenas a versão para impressão")

    args = parser.parse_args()

    # Interatividade (Perguntar o que faltar)
    book_dir = args.book_dir
    while not book_dir:
        book_dir = get_input("1. Qual o nome da pasta do livro? (ex: O_Olhar_Elevado)")

    input_path = os.path.join("inputs", book_dir)
    md_file = os.path.join(input_path, "texto_original.md")
    
    if not os.path.exists(md_file):
        print(f"\n❌ Erro: O arquivo {md_file} não foi encontrado.")
        print("Certifique-se de que a pasta está dentro de 'inputs/'.")
        sys.exit(1)

    book_format = args.format or get_input("2. Qual o formato do livro?", "A5")
    theme = args.theme or get_input("3. Qual a cor do fundo/papel?", "Creme")
    author = args.author or get_input("4. Qual o nome do(a) Autor(a)?", "Carolina Cordaro")
    title = args.title or get_input("5. Qual o Título do livro?", "O Olhar Elevado")
    cover_image = args.cover
    if cover_image is None:
        cover_image = get_input("6. Caminho da capa (Pressione Enter para usar a IA ou padrão)", f"inputs/{book_dir}/assets/capa_olhar_elevado_v2.png")

    config = {
        "book_id": book_dir,
        "format": book_format.upper(),
        "theme": theme.title(),
        "author": author,
        "title": title,
        "cover_image": cover_image,
        "assets_dir": os.path.join(input_path, "assets")
    }

    print("\n--- INCIANDO DIAGRAMAÇÃO ---")
    
    # Passo 1: Parser do Markdown
    print("📝 Lendo e processando Markdown...")
    parsed_sections = process_markdown(md_file, config)

    gen_digital = not args.print_only
    gen_print = not args.digital_only

    # Passo 2: Builder de HTML com Paged.js
    print("🏗️ Construindo versões em HTML com Paged.js...")
    html_print_path = build_html(parsed_sections, config, is_print=True) if gen_print else None
    html_digital_path = build_html(parsed_sections, config, is_print=False) if gen_digital else None

    # Passo 3: Geração do PDF via Playwright
    print("🖨️ Exportando versões em PDF...")
    pdf_print_path = print_pdf(html_print_path, config) if (gen_print and html_print_path) else None
    pdf_digital_path = print_pdf(html_digital_path, config) if (gen_digital and html_digital_path) else None

    print(f"\n✨ Workflow concluído com sucesso!")
    if pdf_print_path:
        print(f"📂 Versão para Gráfica (com marcas de corte e sangria): {pdf_print_path}")
    if pdf_digital_path:
        print(f"📂 Versão Digital (sem marcas, limpa): {pdf_digital_path}")

if __name__ == "__main__":
    main()
