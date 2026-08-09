import os
import re
import base64
import markdown
import sys
import uuid
import tempfile
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup, Tag, NavigableString

def get_image_url(image_path):
    """
    Retorna o schema file:// absoluto da imagem, mas otimiza via PIL 
    antes para evitar que OOM no Chromium durante geração do PDF (Websocket payload limit).
    """
    if not os.path.exists(image_path):
        print(f"⚠️ Aviso: Imagem não encontrada: {image_path}")
        return ""
        
    abs_path = os.path.abspath(image_path)
    
    try:
        from PIL import Image
        
        # Pasta recursiva temporária para as otimizadas
        output_dir = "outputs"
        local_tmp = os.path.join(output_dir, ".opt_imgs")
        if not os.path.exists(local_tmp): os.makedirs(local_tmp)
            
        # Evita processar SVGs que não são lidos pela PIL assim
        if abs_path.lower().endswith(".svg"):
            with open(abs_path, 'rb') as svg_file:
                b64 = base64.b64encode(svg_file.read()).decode('utf-8')
            return f"data:image/svg+xml;base64,{b64}"

        img = Image.open(abs_path)

        # Se for muito massiva, nós ajustamos a dimensão
        max_dim = 1800 # ~300 DPI num A5 impresso não precisa de mais pixels que isso de largura/altura real.
        w, h = img.size
        
        # Só gastamos tempo reprocessando se a imagem for grande
        if w > max_dim or h > max_dim or os.path.getsize(abs_path) > 500000:
            if w > max_dim or h > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                
            out_filename = f"opt_{uuid.uuid4().hex[:8]}.jpg"
            out_path = os.path.join(local_tmp, out_filename)
            
            # Converter para modo RGB antes de salvar como JPEG se era PNG com alpha
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    bg.paste(img, mask=img.split()[3])
                else:
                    bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
                img = bg
            else:
                img = img.convert('RGB')
                
            # Salvar como jpg otimizado
            img.save(out_path, "JPEG", quality=85, optimize=True)
            return f"file://{os.path.abspath(out_path)}"

    except Exception as e:
        print(f"   ⚠️ Aviso: Impossível otimizar a imagem via PIL: {abs_path} - Erro: {e}")

    return f"file://{abs_path}"

def process_markdown(md_file_path, config):
    """Lê o Markdown, converte para HTML e fragmenta por capítulos."""
    with open(md_file_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    lines = md_text.split('\n')
    cleaned_lines = lines # Restaurando todas as imagens
    
    md_text = '\n'.join(cleaned_lines)

    # Marcadores temporários para evitar conflitos iniciais
    md_text = md_text.replace("* [ ]", "TODO_ITEM_EMPTY")
    md_text = md_text.replace("* [x]", "TODO_ITEM_CHECKED")

    lines = md_text.split('\n')
    fixed_lines: list[str] = []
    i = 0
    in_checklist = False
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Lógica de Checklist
        if "TODO_ITEM_EMPTY" in line or "TODO_ITEM_CHECKED" in line:
            if not in_checklist:
                # Verificar se a linha anterior era um pseudo-cabeçalho em negrito
                # Buscamos para trás ignorando linhas vazias
                idx = len(fixed_lines) - 1
                while idx >= 0 and not fixed_lines[idx].strip():
                    idx -= 1
                
                if idx >= 0:
                    prev_line = fixed_lines[idx].strip()
                    if prev_line.startswith("**") and prev_line.endswith("**") and len(prev_line) < 60:
                        # Convertemos para H3 para que as regras de break-after: avoid funcionem
                        header_text = prev_line.strip("*").strip()
                        fixed_lines[idx] = f"### {header_text}"
                
                fixed_lines.append("<ul class='simple-checklist'>")
                in_checklist = True
            
            is_checked = "TODO_ITEM_CHECKED" in line
            marker = "TODO_ITEM_CHECKED" if is_checked else "TODO_ITEM_EMPTY"
            content = line.replace(marker, "").strip()
            checked_class = "checked" if is_checked else ""
            fixed_lines.append(f"<li class='checklist-item {checked_class}'>{content}</li>")
        else:
            if in_checklist and line: # Se houver texto, fecha o container
                fixed_lines.append("</ul>")
                in_checklist = False
            
            # Curativo de tabelas dentro do loop principal
            if line.startswith('|') and (':' in line or '-' in line) and not (line.endswith('|') and line.count('|') >= 2):
                temp_line = line
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if (next_line.startswith('|') or ':' in next_line or '-' in next_line) and len(next_line) < 10:
                        temp_line += next_line
                        if temp_line.endswith('|') and temp_line.count('|') >= 2:
                            i = j
                            break
                    else:
                        break
                    j += 1
                fixed_lines.append(temp_line)
            else:
                # Se for uma lista normal (começa com * )
                # Precisamos garantir que haja uma linha em branco antes do início da lista 
                # para o parser 'sane_lists' funcionar corretamente
                is_normal_list = line.startswith('* ') and "TODO_ITEM" not in line
                if is_normal_list and i > 0 and lines[i-1].strip() and not lines[i-1].strip().startswith('* '):
                    fixed_lines.append("")
                    
                fixed_lines.append(lines[i]) # Mantém a linha original (preservando indentação de listas normais)
        i += 1
    
    if in_checklist:
        fixed_lines.append("</ul>")
        
    md_text = '\n'.join(fixed_lines)

    # Parse Markdown para HTML base (usando sane_lists para listas normais e nl2br para quebras de linha)
    html_raw = markdown.markdown(md_text, extensions=['tables', 'sane_lists', 'nl2br'])
    
    soup = BeautifulSoup(html_raw, 'html.parser')
    
    # Safe word protection (only in text nodes to avoid breaking HTML attributes like alt/src)
    protected_words = [
        "Santa Teresinha", "Teresinha", "barulhentos", "Barulhentos"
    ]
    
    for text_node in soup.find_all(string=True):
        if not text_node.parent or text_node.parent.name in ['script', 'style', 'img', 'code']:
            continue
            
        original_text = str(text_node)
        new_text = original_text
        for word in protected_words:
            if word in new_text:
                new_text = new_text.replace(word, f'<span style="white-space: nowrap;">{word}</span>')
        
        if new_text != original_text:
            # Substituímos o nó de texto por um novo fragmento HTML
            new_fragment = BeautifulSoup(new_text, 'html.parser')
            text_node.replace_with(new_fragment)
    
    # Processar imagens locais para Base64
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and not src.startswith(('http', 'data:')):
            if os.path.isabs(src) and os.path.exists(src):
                img_path = src
            else:
                # Tentar resolver o caminho relativo à pasta assets
                if src.startswith('assets/'):
                    src = src.replace('assets/', '')
                img_path = os.path.join(config['assets_dir'], os.path.basename(src))
            
            img_url = get_image_url(img_path)
            if img_url:
                img['src'] = img_url

    # Identificar seções e evitar duplicatas
    sections: List[Dict[str, Any]] = []
    current_section: Optional[Dict[str, Any]] = None
    seen_elements = set()
    
    # Pegar elementos de nível superior
    elements = soup.contents
    if soup.body:
        elements = soup.body.contents
    
    for element in elements:
        # Pular strings vazias que o BeautifulSoup às vezes coloca entre tags
        if isinstance(element, NavigableString):
            if not element.strip():
                continue
        
        # Evitar re-processar o mesmo elemento (guard contra duplicidade)
        el_id = id(element)
        if el_id in seen_elements:
            continue
        seen_elements.add(el_id)
        
        if isinstance(element, Tag):
            is_header = element.name in ['h1', 'h2', 'h3']
            is_manual_landscape = element.name == 'div' and ('chapter-landscape' in element.get('class', []) or element.find(class_='chapter-landscape'))

            if is_header or is_manual_landscape:
                header_text = ""
                if is_header:
                    header_text = "".join([str(c) for c in element.contents]).strip()
                    if not header_text: continue
                
                # Próximo elemento para ver se é uma tabela (para headers)
                next_element = None
                skipped_tags = []
                if is_header:
                    # Título sugere tabela? Vamos ser mais persistentes na busca
                    is_table_title = "tabela" in header_text.lower()
                    
                    curr = element.next_sibling
                    scan_count = 0
                    while curr and scan_count < 5: # Olhar até 5 elementos (p, strings, etc)
                        if isinstance(curr, NavigableString):
                            if not curr.strip():
                                curr = curr.next_sibling
                                continue
                        if isinstance(curr, Tag):
                            if curr.name == 'table':
                                next_element = curr
                                break
                            if curr.name in ['h1', 'h2', 'h3']: break # Outro header, para aqui
                            
                            # Se for um parágrafo curto ou lista, podemos incluir no landscape
                            if curr.name in ['p', 'ul', 'ol']:
                                if curr.name == 'p' and not is_table_title and len(curr.get_text()) > 200:
                                    break # Parágrafo muito longo fora de contexto
                                skipped_tags.append(curr)
                            
                        curr = curr.next_sibling
                        scan_count += 1
                
                # Se for header seguido de tabela, cria uma seção landscape automática
                if is_header and next_element and next_element.name == 'table':
                    # Consolidar título, lead-in text, tabela e lead-out text
                    all_tags = [element] + skipped_tags + [next_element]
                    
                    landscape_content = "".join([str(t) for t in all_tags])
                    html_wrapped = f'<div class="chapter-landscape"><div class="landscape-inner">{landscape_content}</div></div>'
                    
                    if current_section and current_section["content"]:
                        # Fecha a seção normal anterior (com lead-in se houver)
                        sections.append(current_section)
                    
                    # Adiciona a seção landscape dedicada
                    sections.append({
                        "title": header_text,
                        "tag": "h3",
                        "content": [html_wrapped],
                        "id": f"landscape_{id(element)}",
                        "reading_time": 0,
                        "is_landscape": True
                    })
                    
                    # Marcar como processados
                    seen_elements.add(id(next_element))
                    for t in skipped_tags: seen_elements.add(id(t))
                    
                    # Reiniciar Seção Normal
                    current_section = {
                        "title": "",
                        "tag": "div",
                        "content": [],
                        "id": f"after_{id(element)}",
                        "reading_time": 0,
                        "is_landscape": False
                    }
                    continue
                
                # Se for uma div landscape manual, cria uma seção landscape dedicada
                elif is_manual_landscape:
                    if current_section and current_section["content"]:
                        text_only = "".join(current_section["content"])
                        text_only = BeautifulSoup(text_only, 'html.parser').get_text()
                        word_count = len(re.findall(r'\w+', text_only))
                        current_section["reading_time"] = max(1, round(word_count / 200))
                        sections.append(current_section)
                    
                    sections.append({
                        "title": "Tabela",
                        "tag": "h3",
                        "content": [str(element)],
                        "id": f"landscape_{id(element)}",
                        "reading_time": 0,
                        "is_landscape": True
                    })
                    
                    # Reiniciar Seção Normal para o texto seguinte
                    current_section = {
                        "title": "", # Continuação do texto
                        "tag": "div",
                        "content": [],
                        "id": f"text_{id(element)}",
                        "reading_time": 0,
                        "is_landscape": False
                    }
                    continue

                # Header normal (não landscape) - Iniciar nova seção
                if current_section and current_section["content"]:
                    # Calcular tempo de leitura da seção anterior
                    text_only = "".join(current_section["content"])
                    text_only = BeautifulSoup(text_only, 'html.parser').get_text()
                    word_count = len(re.findall(r'\w+', text_only))
                    current_section["reading_time"] = max(1, round(word_count / 200))
                    sections.append(current_section)
                
                # Novo capítulo ou seção normal
                sec_id = re.sub(r'[\W_]+', '-', header_text.lower())
                element['id'] = sec_id
                
                current_section = {
                    "title": header_text, 
                    "tag": str(element.name),
                    "content": [str(element)],
                    "id": sec_id,
                    "reading_time": 1,
                    "is_landscape": False
                }
                continue
            else:
                if current_section is None:
                    # Se o documento começa sem um H1/H2 (ex: epígrafe), cria uma seção inicial mas sem título
                    current_section = {"title": "", "content": [], "id": "intro", "tag": "h1", "reading_time": 1}
                
                # Se for uma tabela avulsa (sem título imediato antes)
                if element.name == 'table':
                    table_html = f'<div class="table-wrapper"><div class="landscape-inner">{str(element)}</div></div>'
                    current_section["content"].append(table_html)
                else:
                    current_section["content"].append(str(element))
        elif isinstance(element, NavigableString) and element.strip():
            if current_section is None:
                current_section = {"title": "", "content": [], "id": "intro", "tag": "h1", "reading_time": 1}
            current_section["content"].append(str(element))
                
    if current_section and current_section["content"]:
        text_only = "".join(current_section["content"])
        text_only = BeautifulSoup(text_only, 'html.parser').get_text()
        word_count = len(re.findall(r'\w+', text_only))
        current_section["reading_time"] = max(1, round(word_count / 200))
        sections.append(current_section)

    # Post-process to consolidate reading time by chapter (H1)
    last_h1_index = -1
    for i, section in enumerate(sections):
        if section["tag"] == "h1":
            last_h1_index = i
        elif last_h1_index != -1:
            # Add this section's reading time to the parent H1
            sections[last_h1_index]["reading_time"] += section["reading_time"]
            # Set this section's reading time to 0 (it will be hidden in builder)
            section["reading_time"] = 0

    return sections
