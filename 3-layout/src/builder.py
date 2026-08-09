import os
import base64
import json
import re
from datetime import datetime
from src.parser import get_image_url

def build_html(sections, config, is_print=True):
    # CSS logic based on format
    # A5: 148.5 x 210, A4: 210 x 297, Pocket: 125 x 180
    w = "148.5mm"
    h = "210mm"
    if config['format'] == "A4":
        w, h = "210mm", "297mm"
    elif config['format'] == "POCKET":
        w, h = "125mm", "180mm"
        
    theme_bg = "#FDF5E6" if config['theme'] == "Creme" else "#FFFFFF"
    
    # get assets
    cover_image_path = config.get('cover_image')
    if not cover_image_path:
        cover_image_path = os.path.join(config.get('assets_dir', ''), "capa_olhar_elevado_v2.png")
    
    cover_b64 = get_image_url(cover_image_path)
    logo_b64 = get_image_url("resources/logos/ilios/logo-black.svg")
    arabesco_b64 = get_image_url(os.path.join(config.get('assets_dir', ''), "arabesco_inferior.png"))
    
    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Cinzel:wght@400;700&family=Allison&family=Great+Vibes&display=swap');

    :root {{
        --bg-color: {theme_bg};
        --text-color: #2C3E50;
        --accent-color: #5C4033; /* Marrom escuro elegante */
        --earth-tone: #8B4513;   /* Tom terroso para o título */
    }}

    @page {{
        size: {w} {h};
        margin: {"25mm 20mm 25mm 20mm" if is_print else "25mm 20mm"};
        background-color: var(--bg-color);
        { "marks: crop; bleed: 5mm;" if is_print else "marks: none; bleed: 0;" }
    }}

    @page author_page {{ 
        margin: {"20mm 15mm 35mm 25mm" if is_print else "20mm 20mm 35mm 20mm"}; 
        @bottom-left {{
            content: counter(page);
            font-family: 'Libre Baskerville', serif;
            font-size: 9pt;
            color: var(--earth-tone);
        }}
        @bottom-right {{
            content: counter(page);
            font-family: 'Libre Baskerville', serif;
            font-size: 9pt;
            color: var(--earth-tone);
        }}
    }}

    html, body {{
        background-color: var(--bg-color) !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        overflow: visible !important;
    }}
    
    .pagedjs_page {{
        background-color: var(--bg-color) !important;
    }}

    /* Removido o seletor redundante que sobrescrevia margens */

    /* Numeração de Páginas via Paged.js nas margens inferiores */
    @page :left {{
        @bottom-left {{
            content: counter(page);
            font-family: 'Libre Baskerville', serif;
            font-size: 9pt;
            color: var(--earth-tone);
        }}
    }}
    @page :right {{
        @bottom-right {{
            content: counter(page);
            font-family: 'Libre Baskerville', serif;
            font-size: 9pt;
            color: var(--earth-tone);
        }}
    }}

    /* Esconder número de página na capa e folhas especiais */
    @page cover_page {{ 
        size: {w} {h};
        margin: 0; 
        marks: none; 
        @bottom-left{{content: none;}} 
        @bottom-right{{content: none;}} 
    }}
    @page title {{ margin: {"20mm 15mm 25mm 25mm" if is_print else "20mm"}; @bottom-left{{content: none;}} @bottom-right{{content: none;}} }}
    @page blank_page {{ @bottom-left{{content: none;}} @bottom-right{{content: none;}} }}
    @page toc_page {{ margin: 30mm 15mm 25mm 15mm; @bottom-left{{content: none;}} @bottom-right{{content: none;}} }}
    @page epigraph_page {{ margin: {"25mm 20mm 25mm 30mm" if is_print else "25mm 20mm"}; @bottom-left{{content: none;}} @bottom-right{{content: none;}} }}
    
    @page chapter_landscape {{ 
        size: {w} {h}; 
        margin: 20mm;
        @bottom-left {{ content: none; }}
        @bottom-right {{ content: none; }}
    }}
    
    /* Sobre a Autora - Título sozinho na página */
    #section_sobre_a_autora {{
        page: author_page;
    }}

    #section_sobre_a_autora .chapter-header {{
        height: 160mm !important; 
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        break-after: page !important;
        page-break-after: always !important;
        border: none !important;
        margin-bottom: 0 !important;
    }}
    #section_sobre_a_autora .chapter-header .reading-time {{
        display: none !important;
    }}
    #section_sobre_a_autora img {{
        display: block !important;
        margin: 0 auto 30px auto !important;
        max-height: 260px !important;
        object-fit: contain !important;
        break-before: page !important;
        page-break-before: always !important;
    }}
    #section_sobre_a_autora p {{
        break-inside: avoid !important;
        page-break-inside: avoid !important;
        margin-bottom: 1.5em !important;
    }}
    body {{
        font-family: 'Libre Baskerville', serif;
        font-size: 12px;
        line-height: 1.5;
        color: var(--text-color);
        background-color: var(--bg-color);
        text-align: justify;
        text-align-last: left;
        orphans: 3;
        widows: 3;
        hyphens: none;
        -webkit-hyphens: none;
        -moz-hyphens: none;
        -ms-hyphens: none;
        overflow-wrap: break-word; /* Proteção extra contra estouro */
        line-break: strict;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
        text-rendering: optimizeLegibility;
    }}
    
    p, li, blockquote, .simple-checklist li {{
        orphans: 4 !important;
        widows: 4 !important;
        margin-bottom: 1.2em;
        break-inside: auto !important;
        page-break-inside: auto !important;
        overflow: visible !important;
        position: relative;
        hyphens: none !important;
    }}
    
    /* Evitar que itens de lista curtos sejam quebrados */
    li {{
        break-inside: avoid-page !important;
    }}

    h1, h2, h3, h4, .chapter-title {{
        break-inside: avoid !important;
        page-break-inside: avoid !important;
        break-after: avoid !important;
        hyphens: none !important; 
        -webkit-hyphens: none !important;
        orphans: 2;
        widows: 2;
        line-height: 1.3;
        margin-bottom: 0.5em;
    }}
    
    .section-content {{
        width: 100%;
        box-sizing: border-box;
    }}
    
    .first-section {{
        break-before: auto !important;
        page-break-before: auto !important;
    }}
    
    * {{
        box-sizing: border-box;
    }}
    
    h1, h2, h3, h4, .chapter-title, h3 + p, h3 + ul, h3 + ol {{
        break-after: avoid !important;
        page-break-after: avoid !important;
    }}

    .epigraph-container {{
        page: epigraph_page;
        { "break-before: right;" if is_print else "break-before: page;" }
        height: {h};
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: flex-end; /* Texto à direita */
        text-align: right;
        text-align-last: auto;
    }}
    
    .first-section .epigraph-container {{
        break-before: auto !important;
        page-break-before: auto !important;
        height: auto !important;
        min-height: 100mm;
        margin-top: 20mm;
    }}

    .epigraph {{
        font-style: italic;
        font-size: 1.1em;
        color: var(--earth-tone);
        max-width: 75%;
        line-height: 1.6;
    }}

    h1, h2 {{
        color: #111;
        font-weight: 700;
        font-style: italic;
        text-align: center;
        text-align-last: center;
        break-after: avoid;
        page-break-after: avoid;
    }}

    h3, h4 {{
        color: #111;
        font-weight: 700;
        font-style: italic;
        text-align: left;
        text-align-last: left;
        break-after: avoid !important;
        page-break-after: avoid !important;
        margin-top: 1.5em;
    }}

    /* Força que o elemento após o H3 não quebre de página */
    h3 + ul, h3 + p, h3 + .reading-time {{
        break-before: avoid !important;
    }}

    blockquote, blockquote p {{
        text-align: right !important;
        text-align-last: right !important;
        font-style: italic;
        margin-left: 20%;
        margin-right: 0;
        color: var(--earth-tone);
        border: none;
        padding: 0;
        break-inside: avoid !important;
        page-break-inside: avoid !important;
    }}
    
    a {{
        word-break: normal;
        overflow-wrap: break-word;
    }}

    /* Tabelas Premium */
    /* Tabelas Premium - Forçadas a ocupar página inteira e horizontal se necessário */
    /* CAPÍTULOS HORIZONTAIS (TABELAS ROTACIONADAS) */
    .chapter-landscape {{
        page: chapter_landscape !important;
        display: block !important;
        text-align: center;
        width: 100%;
        height: 100%;
        margin: 0 !important;
        padding: 0 !important;
        position: relative !important;
        overflow: visible !important; 
        background-color: var(--bg-color) !important;
    }}

    .landscape-inner {{
        width: 155mm !important; /* Margem lateral aumentada (210 - 55) */
        height: 105mm !important; /* Margem vertical (148.5 - 43.5) */
        position: absolute !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) rotate(90deg) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important; /* Centralizar para melhor estética */
        align-items: center !important;
        padding: 5mm !important;
        box-sizing: border-box !important;
        overflow: visible !important;
    }}

    .landscape-inner p {{
        text-align: left !important;
        width: 100% !important;
        margin-bottom: 8px !important;
        font-size: 8.5pt !important; /* Fonte menor no landscape conforme pedido */
        line-height: 1.2 !important;
    }}

    .landscape-title {{
        font-family: 'Playfair Display', serif;
        font-size: 1.3em;
        margin-bottom: 0.4em;
        text-align: center;
        color: var(--earth-tone);
    }}

    table {{
        width: 94%;
        border-collapse: separate;
        border-spacing: 0;
        margin: 20px auto;
        font-size: 8pt; /* Fonte menor conforme pedido */
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        overflow: visible;
    }}

    /* Estilo para tabelas que devem ser lidas na horizontal */
    .table-wrapper table {{
        width: 94%;
        margin: 0 auto;
        border-collapse: collapse;
        table-layout: fixed !important; /* Força larguras fixas para evitar overlap */
        break-inside: avoid !important;
        page-break-inside: avoid !important;
    }}

    /* Prevenir repetição de cabeçalho em tabelas que não devem quebrar */
    .table-wrapper thead {{
        display: table-header-group;
    }}
    
    .table-wrapper table th:nth-child(1), .table-wrapper table td:nth-child(1) {{
        width: 25%;
    }}
    .table-wrapper table th:nth-child(2), .table-wrapper table td:nth-child(2) {{
        width: 38%;
    }}
    .table-wrapper table th:nth-child(3), .table-wrapper table td:nth-child(3) {{
        width: 37%;
    }}

    .table-wrapper th, .table-wrapper td {{
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal;
        hyphens: auto;
        word-break: normal;
        font-size: 8pt;
        padding: 6px 4px;
        border: 1px solid #e0e0e0;
        line-height: 1.1;
    }}

    /* Larguras removidas para permitir layout automático mais flexível */

    th {{
        background-color: var(--accent-color);
        color: white;
        text-align: center;
        text-align-last: center;
        padding: 2mm 4mm;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        hyphens: none;
    }}

    td {{
        padding: 2mm 4mm;
        border-bottom: 1px solid #f0f0f0;
        line-height: 1.3;
        vertical-align: top;
        text-align: left !important;
        text-align-last: left !important;
        hyphens: none;
    }}

    tr:nth-child(even) td {{
        background-color: rgba(237, 224, 212, 0.3);
    }}

    tr:last-child td {{
        border-bottom: none;
    }}

    /* Checklists Minimalistas */
    .simple-checklist {{
        list-style: none;
        padding: 0;
        margin: 1.5em 0;
    }}

    .checklist-item {{
        position: relative;
        padding-left: 30px;
        margin-bottom: 2mm;
        line-height: 1.5;
        display: block;
        font-size: 11pt;
    }}

    .checklist-item::before {{
        content: "";
        position: absolute;
        left: 0;
        top: 2px;
        width: 16px;
        height: 16px;
        border: 2px solid var(--accent-color);
        border-radius: 4px;
        background-color: transparent;
    }}
    
    .checklist-item.checked::before {{
        background-color: var(--accent-color);
    }}

    .checklist-item.checked::after {{
        content: "✓";
        position: absolute;
        left: 3px;
        top: -2px;
        color: white;
        font-size: 14px;
        font-weight: bold;
    }}

    .cover-page {{
        page: cover_page;
        width: 100%;
        height: 100%;
        position: relative;
        margin: 0;
        padding: 0;
        background-color: #000;
        {f"background-image: url('{cover_b64}');" if cover_b64 else ""}
        background-size: cover !important;
        background-position: center center !important;
        background-repeat: no-repeat !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        text-align: center;
        box-sizing: border-box;
        padding-top: 15%;
        padding-bottom: 10%;
        overflow: hidden;
        z-index: 1;
    }}

    .cover-title-container {{
        z-index: 2;
        text-align: center;
    }}

    .cover-title {{
        font-family: 'Cinzel', serif !important;
        font-size: 58pt;
        color: #f7ecd5;
        text-shadow: 0px 4px 15px rgba(0,0,0,0.9);
        margin: 0;
        line-height: 1.1;
        font-weight: 700;
        text-transform: none !important;
    }}

    .cover-subtitle {{
        font-family: 'Playfair Display', serif !important;
        font-size: 16pt;
        color: #dbb666;
        letter-spacing: 4px;
        margin-top: 15px;
        text-shadow: 0px 2px 10px rgba(0,0,0,0.9);
        text-transform: uppercase;
        font-weight: 400;
    }}

    .cover-footer {{
        z-index: 2;
        display: flex;
        flex-direction: column;
        align-items: center;
    }}

    .cover-author {{
        font-family: 'Allison', cursive !important;
        font-size: 52pt;
        color: #f7ecd5;
        margin-bottom: 25px;
        text-shadow: 0px 2px 10px rgba(0,0,0,0.9);
        font-weight: normal;
        text-transform: none !important;
        letter-spacing: 0 !important;
    }}

    .cover-logo {{
        width: 60mm;
        filter: drop-shadow(0px 2px 8px rgba(0,0,0,0.8));
    }}

    /* Folha de Rosto (Página 2) */
    .title-page {{
        page: title;
        { "break-before: right;" if is_print else "break-before: page;" }
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100%;
        text-align: center;
        text-align-last: center;
        hyphens: none;
        color: #8B4513;
    }}
    
    .title-page-main {{
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    
    .title-page-title {{
        font-family: 'Great Vibes', cursive;
        font-size: 40pt;
        margin-bottom: 5mm;
    }}
    
    .title-page-subtitle {{
        font-size: 14pt;
        text-transform: uppercase;
        letter-spacing: 1px;
        max-width: 80%;
        margin: 0 auto;
    }}
    
    .title-page-footer {{
        margin-bottom: 20mm;
    }}

    .logo-ilios {{
        height: 25mm;
        width: auto;
        margin-top: 5mm;
    }}

    /* SUMÁRIO PROFISSIONAL (Paged.js) */
    .toc-page {{
        page: toc_page;
        padding: 0;
        break-after: auto !important;
    }}
    .toc-page h1 {{ 
        text-align: center; 
        font-family: 'Playfair Display', serif; 
        margin-top: 0;
        margin-bottom: 0.5em; 
        font-size: 2.5em; 
    }}
    
    #toc-list {{ 
        list-style: none; 
        padding: 0; 
        font-size: 9pt;
    }}
    #toc-list li {{ 
        clear: both;
        line-height: 12pt;
    }}
    
    #toc-list a {{ 
        color: inherit; 
        text-decoration: none;
        display: flex;
        align-items: baseline;
        position: relative;
    }}
    
    #toc-list a::after {{
        content: "";
        flex: 1;
        border-bottom: 1px dotted #ccc;
        margin: 0 10px;
        order: 2;
    }}

    .toc-title {{
        order: 1;
        text-align: left;
        hyphens: none !important;
        word-break: normal !important;
        overflow-wrap: normal !important;
    }}

    .toc-page-num {{
        order: 3;
        min-width: 20px;
        font-variant-numeric: tabular-nums;
        font-weight: bold;
        font-family: 'Libre Baskerville', serif;
        text-align: right;
    }}

    /* Estilos Hierárquicos com Indentação */
    #toc-list .toc-h1 {{
        font-weight: bold;
        text-transform: uppercase;
        margin-top: 0.1em;
    }}
    
    #toc-list .toc-h2 {{
        padding-left: 5mm;
        font-weight: normal;
        margin-top: 0;
    }}
    
    #toc-list .toc-h3 {{
        padding-left: 10mm;
        font-size: 9pt;
        color: #666;
        margin-top: 0;
    }}

    #toc-list .toc-h2 .toc-page-num,
    #toc-list .toc-h3 .toc-page-num {{
        font-weight: normal;
    }}

    /* CAPÍTULOS */
    .chapter {{
        { "break-before: right;" if is_print else "break-before: page;" }
    }}
    
    .chapter h1, .chapter h2 {{
        font-family: 'Playfair Display', serif;
        text-align: center;
        margin-top: 15vh;
        margin-bottom: 1.5em;
        font-size: 2em;
    }}

    .chapter h2 {{
        font-size: 1.5em;
        margin-top: 4vh;
    }}

    /* Arabesco Inferior abaixo do Título Paged Media */
    .chapter-heading-ornament {{
        width: 200px;
        height: 60px;
        margin: 0 auto 3em auto;
        opacity: 0.8;
        { f"background-image: url('{arabesco_b64}');" if arabesco_b64 else "" }
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        mix-blend-mode: multiply; /* Remove o fundo branco se a imagem não for transparente */
        break-after: avoid;
        page-break-after: avoid;
    }}

    .reading-time {{
        text-align: center;
        text-align-last: center;
        font-size: 0.85em;
        font-style: italic;
        color: var(--accent-color);
        margin-bottom: 2em;
        display: block;
        break-after: avoid;
        page-break-after: avoid;
    }}

    .chapter-break {{
        page-break-before: always;
        break-before: page;
        margin-top: 2em;
    }}

    /* Tabelas, Imagens e Checklists do Markdown */
    img {{ 
        max-width: 80%; 
        border-radius: 4px; 
        display: block; 
        margin: 0.8em auto; 
        object-fit: contain; 
        max-height: 48vh; 
        page-break-inside: avoid; 
        break-inside: avoid; 
    }}
    
    /* Estilo Especial: Sobre a Autora (Harmonizado) */
    .author-section {{
        background: transparent;
        padding: 0;
        border: none;
        margin: 10mm 0;
        break-before: page;
        page-break-before: always;
        break-inside: auto;
        page-break-inside: auto;
        overflow: visible !important;
    }}

    .author-section h2 {{
        font-family: 'Playfair Display', serif !important;
        font-size: 2.2em !important;
        margin-top: 2vh !important;
        margin-bottom: 0.5em !important;
        color: var(--earth-tone) !important;
        font-style: italic !important;
        text-align: center;
    }}

    .author-section img {{
        max-width: 40%;
        height: auto;
        border-radius: 4px;
        box-shadow: none;
        border: 1px solid #e2d8ce;
        margin: 5mm auto 5mm auto;
        display: block;
    }}

    /* Estilo para as imagens do QR Code na seção da autora */
    .author-section img[src*="QRCode"], .author-section img[src*="QRCODE"] {{
        width: 28mm !important;
        height: 28mm !important;
        display: block;
        margin: 2mm auto;
        border-radius: 2px;
        box-shadow: none;
        border: 1px solid #e2d8ce;
        background: white;
        padding: 3px;
    }}

    .author-section ul {{
        list-style: none;
        padding: 0;
        margin-top: 15mm;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10mm;
    }}

    .author-section li {{
        text-align: center;
        margin-bottom: 0;
        font-size: 9pt;
        background: none;
        padding: 0;
        border-radius: 0;
        border-top: 1px solid #e2d8ce;
        padding-top: 5mm;
        color: var(--earth-tone);
    }}

    .author-section li a {{
        color: var(--accent-color);
        text-decoration: none;
        font-weight: bold;
    }}

    .author-section p {{
        font-family: 'Libre Baskerville', serif;
        font-size: 11pt;
        line-height: 1.4;
        text-align: justify;
        margin-bottom: 1.2em;
        orphans: 2 !important;
        widows: 2 !important;
    }}

    .author-contact-wrapper {{
        page-break-before: always;
        break-before: page;
        margin-top: 10mm;
        font-family: 'Libre Baskerville', serif;
    }}
    
    .author-contact-wrapper strong {{
        color: var(--accent-color);
        font-family: 'Playfair Display', serif;
    }}

    .contact-item {{
        text-align: center;
        margin-bottom: 2mm;
        border-bottom: 1px solid #e2d8ce;
        padding: 4mm 0;
        font-size: 11pt;
    }}
    
    .contact-item:first-child {{
        border-top: 1px solid #e2d8ce;
    }}

    .qr-row {{
        display: flex;
        justify-content: space-around;
        text-align: center;
        margin-top: 12mm;
    }}

    .qr-col {{
        flex: 1;
        font-size: 11pt;
    }}

    .qr-col img {{
        width: 140px;
        height: 140px;
        border: 1px solid #e2d8ce;
        padding: 5px;
        background: white;
        margin-top: 15px;
        border-radius: 8px;
    }}

    """

    
    # Separando Título de Subtítulo
    main_title = config['title']
    subtitle = ""
    if ":" in main_title:
        parts = main_title.split(":", 1)
        main_title = parts[0].strip()
        subtitle = parts[1].strip()
    elif main_title == "O Olhar Elevado":
        subtitle = "Resgatando o Brincar e o Vínculo na Essência da Simplicidade"

    # Build TOC entries
    toc_entries_html = ""
    for section in sections:
        # Pular seções vazias para evitar páginas em branco
        if not section.get('content') or not "".join(section['content']).strip():
            continue
            
        sec_id = section['id']
        sec_title = section['title']
        
        # Filtros globais para o sumário para evitar itens genéricos ou repetidos
        clean_title = sec_title.lower().strip()
        if not clean_title: continue
        
        # Só ignoramos se for "Intro" vazio ou se for o próprio Sumário/Índice
        if clean_title == "intro" or "sumário" in clean_title or "índice" in clean_title: 
            continue
        if clean_title == "cover" or clean_title == "copyright":
            continue
            
        tag = section.get('tag', 'h1')
        if tag == 'h1':
            toc_class = "toc-h1"
        elif tag == 'h2':
            toc_class = "toc-h2"
        else:
            toc_class = "toc-h3"
            
        toc_entries_html += f'<li class="{toc_class}"><a href="#section_{sec_id}"><span class="toc-title">{sec_title}</span><span class="toc-page-num" data-href="#section_{sec_id}">-</span></a></li>\n'

    # HTML Base
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{config['title']}</title>
    <style>{css}</style>
    <!-- Paged.js Script para calcular quebras e TOC -->
    <script src="https://unpkg.com/pagedjs/dist/paged.polyfill.js"></script>
    <script>
        class TocHandlers extends Paged.Handler {{
            constructor(chunker, polisher, caller) {{
                super(chunker, polisher, caller);
            }}

            afterRendered(pages) {{
                // Preencher números de página nas spans do TOC
                const tocItems = document.querySelectorAll(".toc-page-num");
                tocItems.forEach(item => {{
                    const targetId = item.getAttribute("data-href").substring(1);
                    const targetElement = document.getElementById(targetId);
                    if (targetElement) {{
                        const page = targetElement.closest(".pagedjs_page");
                        if (page) {{
                            const pageNumber = page.getAttribute("data-page-number");
                            item.textContent = pageNumber;
                        }}
                    }}
                }});
            }}
        }}
        Paged.registerHandlers(TocHandlers);
    </script>
</head>
<body>
    
    <!-- Capa -->
    <div class="cover-page">
        <div class="cover-title-container">
            <div class="cover-title">{main_title}</div>
            {f'<div class="cover-subtitle">{subtitle}</div>' if subtitle else ''}
        </div>
        
        <div class="cover-footer">
            <div class="cover-author">{config['author']}</div>
            <img class="cover-logo" src="{logo_b64}">
        </div>
    </div>

    <!-- Folha de Rosto -->
    <div class="title-page">
        <div class="title-page-main">
            <div class="title-page-title">{main_title}</div>
            {f'<div class="title-page-subtitle">{subtitle}</div>' if subtitle else ''}
        </div>
        <div class="title-page-footer">
            <img class="logo-ilios" src="{logo_b64}">
        </div>
    </div>

    <!-- Sumário (Gerado via Python) -->
    <div class="toc-page">
        <h1 class="toc-title">Sumário</h1>
        <ul id="toc-list">
            {toc_entries_html}
        </ul>
    </div>
"""

    # Inserir Conteúdo (Capítulos)
    for i, section in enumerate(sections):
        sec_id = section['id']
        sec_title = section['title']
        tag = section['tag']
        
        # Ignorar Renderizar Sumario/indice que venha escrito no MD
        if "sumário" in sec_title.lower() or "índice" in sec_title.lower():
            continue
            
        content_lines = section['content']
        reading_time = section.get('reading_time', 1)
        
        # Remove a primeira linha se for o Header exato, para substituir pela nossa class custom
        if content_lines and content_lines[0].startswith('<h'):
            content_lines = content_lines[1:]
            
        # Adicionar tempo de leitura APENAS no H1 e se for maior que zero
        time_html = ""
        if tag == 'h1' and reading_time > 0:
            time_html = f'<div class="reading-time">Tempo de leitura estimado: {reading_time} min</div>'
        
        processed_content = content_lines

        # Determinar se remove ornamentos e tempo de leitura
        is_empty_intro = i == 0 and (not sec_title or "introdução" in sec_title.lower())
        is_landscape = section.get('is_landscape', False)
        is_author = "sobre a autora" in sec_title.lower()
        is_cap2 = "filtro de avaliação de brinquedos" in sec_title.lower() or "tabela comparativa" in sec_title.lower()
        
        # Ornamentos e Tempo de leitura apenas no H1
        # Suprime o título visual se for landscape (já está dentro do landscape-inner)
        if is_landscape:
            header_html = f'<{tag} class="chapter-title" id="{sec_id}" style="font-size: 0; margin:0; padding:0; visibility: hidden; position: absolute;">{sec_title}</{tag}>'
        else:
            header_html = f'<{tag} class="chapter-title" id="{sec_id}">{sec_title}</{tag}>'
            
        ornament_html = '<div class="chapter-heading-ornament"></div>' if tag == 'h1' and not is_landscape else ""
        time_html = f'<div class="reading-time">Tempo de leitura estimado: {reading_time} min</div>' if tag == 'h1' else ""
        
        div_class = "chapter"
        if i == 0:
            div_class += " first-section"
        if is_landscape:
            div_class += " chapter-landscape" # Classe para controlar quebra única
        if is_author:
            div_class += " author-section"
            time_html = "" # Remove tempo de leitura para a autora
            ornament_html = "" # Removido ornamento a pedido do usuário
        
        # Se for a seção técnica inicial (que costuma ter a epígrafe), 
        # Mantemos o título se for "Introdução" (user feedback)
        if is_empty_intro:
            header_html = f'<h1 class="chapter-title" id="{sec_id}">{sec_title}</h1>' if sec_title else ""
            ornament_html = ""
            time_html = ""
        elif is_cap2:
            # Usuário pediu para remover a imagem deste capítulo (Anexo 3)
            ornament_html = ""

        # Pular seções vazias para evitar páginas em branco no corpo do livro
        # Só pula se realmente NÃO houver conteúdo algum (nem texto, nem imagem, nem tabela)
        full_content = "".join(processed_content)
        has_content = bool(re.search(r'<p|<img|<table|<ul|<ol|blockquote|<h\d', full_content, re.I))
        
        if not has_content and not header_html:
            continue

        # Proteção contra página em branco após Sumário e antes de tabelas horizontais
        section_tag = "section" if is_landscape else "div"
        if i == 0:
            break_rule = "break-before: avoid !important; page-break-before: avoid !important;"
        elif is_landscape:
            # A troca de orientação de página já força a quebra, 'auto' evita quebras duplicadas
            break_rule = "break-before: auto !important;"
        else:
            break_rule = "break-before: page !important;"
        
        html += f"""
    <{section_tag} class="{div_class}" id="section_{sec_id}" style="{break_rule}">
        <div class="header-protection" style="break-inside: avoid !important; page-break-inside: avoid !important; break-after: avoid !important; position: relative; display: block;">
            {header_html}
            {ornament_html}
            {time_html}
        </div>
        <div class="section-content">
            {"".join(processed_content)}
        </div>
    </{section_tag}>
"""

    html += """
</body>
</html>
"""
    
    # Save the file
    output_base = os.path.join("outputs", config['book_id'])
    output_htmls = os.path.join(output_base, "htmls")
    if not os.path.exists(output_htmls): os.makedirs(output_htmls)
    
    suffix = "impresso" if is_print else "digital"
    output_path = os.path.join(output_htmls, f"{config['book_id']}_{suffix}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return output_path
