import re
import os

filepath = "/Users/gabrielpereira/Desktop/Projetos/Livros/inputs/A_mae_forte/texto_original.md"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    match_dia = re.match(r'^### \**DIA (\d+).*', line)
    match_conclusao = re.match(r'^### \**CONCLUSÃO.*', line)
    
    if match_dia or match_conclusao:
        # Strip the newlines and markdown characters, then wrap in HTML center
        clean_text = line.strip()
        new_lines.append(f'<h3 align="center">{clean_text.replace("### ", "")}</h3>\n')
    else:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Títulos centralizados com sucesso!")
