import re
import os

filepath = "/Users/gabrielpereira/Desktop/Projetos/Livros/inputs/A_mae_forte/texto_original.md"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []

for i, line in enumerate(lines):
    # Remove existing image markdown
    if re.match(r'^\s*!\[.*\]\(.*\)\s*$', line):
        continue
    
    # If it's a separator, let's insert arabesque before it
    if re.match(r'^\s*---\s*$', line):
        new_lines.append("\n<div style=\"text-align: center; margin-top: 40px; margin-bottom: 40px;\">\n  <img src=\"./assets/arabesco_inferior.png\" width=\"200\">\n</div>\n\n")
        new_lines.append(line)
        continue

    new_lines.append(line)

    # Check for DIA heading
    match_dia = re.match(r'^### \**DIA (\d+).*', line)
    match_conclusao = re.match(r'^### \**CONCLUSÃO.*', line)
    
    if match_dia:
        dia_num = match_dia.group(1)
        new_lines.append(f"\n![Dia {dia_num}](./assets/dia_{dia_num}.jpeg)\n\n")
    elif match_conclusao:
        new_lines.append(f"\n![Conclusão](./assets/conclusao.jpeg)\n\n")

# Also let's append an arabesque at the very end of the file if not there
new_lines.append("\n<div style=\"text-align: center; margin-top: 40px; margin-bottom: 40px;\">\n  <img src=\"./assets/arabesco_inferior.png\" width=\"200\">\n</div>\n")

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Diagramação de imagens concluída!")
