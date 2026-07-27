import os
import subprocess
import tempfile
import shutil
import re
from playwright.sync_api import sync_playwright

def print_pdf(html_path, config):
    import os, tempfile
    from playwright.sync_api import sync_playwright

    abs_html = os.path.abspath(html_path)
    output_htmls_dir = os.path.dirname(abs_html)
    output_dir = os.path.dirname(output_htmls_dir) # Sobe um nivel para outputs/<book_id>/
    if not os.path.exists(output_dir): os.makedirs(output_dir)
        
    # FIX MAC OS TCC / APP SANDBOX EPERM mkdtemp para Playwright
    # Necessário para que PLAYWRIGHT consiga criar suas pastas de usuário no mac sandbox (IDE)
    original_tmpdir = os.environ.get("TMPDIR")
    local_tmp = os.path.abspath(os.path.join("outputs", ".tmp"))
    if not os.path.exists(local_tmp): os.makedirs(local_tmp)
    os.environ["TMPDIR"] = local_tmp
    tempfile.tempdir = local_tmp

    base_name = os.path.basename(html_path).replace(".html", ".pdf")
    output_pdf = os.path.join(output_dir, base_name)
    file_url = f"file://{abs_html}"

    print(f"   [Playwright] Abrindo navegador headless para {base_name}...")
    
    try:
        with sync_playwright() as p:
            chromium_args = [
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--js-flags=--max-old-space-size=10240",
                "--disable-ipc-flooding-protection"
            ]
                
            browser = p.chromium.launch(headless=True, args=chromium_args)
            page = browser.new_page()
                
            print("   [Playwright] Carregando HTML e aguardando polyfill (Paged.js)...")
            page.emulate_media(media="print")
            page.goto(file_url, wait_until="load")
                
            try:
                page.wait_for_selector(".pagedjs_pages", timeout=60000)
                # Aguardar um pouco mais para fontes e quebras renderizarem no DOM
                page.wait_for_timeout(5000)
                print("   [Paged.js] Paginação e Sumário calculados com sucesso!")
            except Exception as e:
                print(f"   [Aviso] Paged.js demorou a responder ou não detectado: {e}")

            print("   [Playwright] Tentando imprimir PDF final via IPC...")
            try:
                page.pdf(
                    path=output_pdf,
                    print_background=True,
                    prefer_css_page_size=True,
                    display_header_footer=False
                )
                print("   ✅ PDF salvo nativamente sem OOM!")
            except Exception as pdf_e:
                print(f"   ⚠️ Playwright OOM Crash (provável IO.read): {pdf_e}")
                print(f"   [Fallback Híbrido] Extraindo DOM estático do Playwright para CLI Headless Nativo...")
                
                page.evaluate("""() => {
                    // Bake pagedjs default counters
                    const pagedjsCounters = document.querySelectorAll('.pagedjs_target_counter');
                    pagedjsCounters.forEach(c => {
                        const style = window.getComputedStyle(c, '::after');
                        let text = style.content;
                        if (text && text !== 'none' && text !== '""') {
                            c.innerText = text.replace(/"/g, '');
                        }
                    });
                    
                    // Bake our custom .toc-page-num
                    const customCounters = document.querySelectorAll('.toc-page-num');
                    customCounters.forEach(item => {
                        if (item.textContent === '-' || item.textContent === '0' || !item.textContent) {
                            const targetId = item.getAttribute("data-href").substring(1);
                            const targetElement = document.getElementById(targetId);
                            if (targetElement) {
                                const pagedPage = targetElement.closest(".pagedjs_page");
                                if (pagedPage) {
                                    item.textContent = pagedPage.getAttribute("data-page-number");
                                }
                            }
                        }
                    });
                }""")
                
                computed_html = page.evaluate("() => document.documentElement.outerHTML")
                generate_fallback_pdf(computed_html, output_pdf, base_name, config, local_tmp)

            browser.close()
    except Exception as launch_e:
        print(f"   ❌ Erro Crítico no Playwright (Launch): {launch_e}")
        print(f"   [Fallback CLI Direto] Tentando imprimir via CLI Headless Nativo (Sem Interação JS)...")
        
        # Fallback direto usando o HTML original
        with open(abs_html, "r", encoding="utf-8") as f:
            original_html = f.read()
        
        generate_fallback_pdf(original_html, output_pdf, base_name, config, local_tmp)
        
    return output_pdf

def generate_fallback_pdf(html_content, output_pdf, base_name, config, local_tmp):
    import subprocess
    import PyPDF2
    import re
    
    # Injetar o fix de tamanho de página correto
    fmt = config.get("format", "A5").upper()
    w_mm, h_mm = 148.5, 210.0
    if fmt == "A4": w_mm, h_mm = 210.0, 297.0
    elif fmt == "POCKET": w_mm, h_mm = 125.0, 180.0
    
    is_print_version = "impresso" in base_name
    if is_print_version:
        w_mm += 40.0 
        h_mm += 40.0
    
    letter_fix = f"<style>@page {{ size: {w_mm}mm {h_mm}mm; margin: 0; }} body {{ margin: 0 !important; padding: 0 !important; overflow: visible !important; }}</style>"
    if "</head>" in html_content.lower():
        html_content = html_content.replace("</head>", f"{letter_fix}</head>")
    else:
        html_content = letter_fix + html_content

    rendered_html_path = os.path.join(local_tmp, f"fallback_{base_name}.html")
    with open(rendered_html_path, "w", encoding="utf-8") as rf:
        rf.write(html_content)
        
    raw_pdf_path = os.path.join(local_tmp, f"raw_{base_name}")
    
    # Tenta localizar o binário do Playwright ou Chrome no Mac
    possible_chromes = [
        os.path.join(os.path.expanduser("~"), "Library/Caches/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-mac-arm64/chrome-headless-shell"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "chrome-headless-shell",
        "google-chrome"
    ]
    
    mac_chrome = None
    for path in possible_chromes:
        if os.path.exists(path) or shutil.which(path):
            mac_chrome = path
            break
            
    if not mac_chrome:
        print("   ❌ Erro: Nenhum binário do Chrome encontrado para o fallback!")
        return

    cmd = [
        mac_chrome,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={raw_pdf_path}",
        f"file://{os.path.abspath(rendered_html_path)}"
    ]
    
    print(f"   [Fallback] Executando {os.path.basename(mac_chrome)} CLI...")
    subprocess.run(cmd, capture_output=True, text=True)
    
    if not os.path.exists(raw_pdf_path) and os.path.exists(raw_pdf_path + ".pdf"):
        raw_pdf_path += ".pdf"
    
    if os.path.exists(raw_pdf_path):
        w_pt = w_mm * 2.83465
        h_pt = h_mm * 2.83465
        
        reader = PyPDF2.PdfReader(raw_pdf_path)
        writer = PyPDF2.PdfWriter()
        
        for p_num in range(len(reader.pages)):
            p_obj = reader.pages[p_num]
            from PyPDF2.generic import RectangleObject
            box = RectangleObject([0, 0, w_pt, h_pt])
            p_obj.mediabox = box
            p_obj.cropbox = box
            writer.add_page(p_obj)
            
        with open(output_pdf, "wb") as f_out:
            writer.write(f_out)
        print(f"   ✅ PDF salvo via Fallback CLI em {output_pdf}")
    else:
        print(f"   ❌ Erro: Falha ao gerar PDF bruto em {raw_pdf_path}")
        
    return output_pdf
