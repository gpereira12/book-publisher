
import PyPDF2
import sys
import os

def inspect_pdf(path):
    if not os.path.exists(path):
        print(f"Erro: Arquivo {path} não encontrado.")
        return

    reader = PyPDF2.PdfReader(path)
    print(f"\n--- Inspecionando PDF: {path} ---")
    print(f"Número de páginas: {len(reader.pages)}")
    
    for i, page in enumerate(reader.pages):
        print(f"\nPágina {i+1}:")
        print(f"  MediaBox: {page.mediabox}")
        print(f"  CropBox: {page.cropbox}")
        print(f"  BleedBox: {page.get('/BleedBox')}")
        print(f"  TrimBox: {page.get('/TrimBox')}")
        
        # Tentar ver se há conteúdo de texto
        text = page.extract_text()
        print(f"  Texto extraído (primeiros 100 caracteres): {text[:100].strip() if text else 'NENHUM TEXTO ENCONTRADO'}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_pdf(sys.argv[1])
    else:
        print("Uso: python inspect_pdf.py <caminho_do_pdf>")
