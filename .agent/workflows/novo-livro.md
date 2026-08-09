---
description: Como criar e estruturar um novo projeto de livro do zero.
---

# Fluxo de Trabalho: Novo Livro (/novo-livro)

Este workflow guia a criação de um novo projeto literário, garantindo que todas as skills e estruturas de pastas sejam aplicadas corretamente.

## Passo a Passo

### 1. Inicialização do Projeto
Crie a pasta do livro dentro do diretório `/Livros/` e inicialize o arquivo de metadados. Se já existir apenas criar o info.md

// turbo
1. Se não houver pasta, execute `mkdir -p "/Users/gabrielpereira/Desktop/Livros/livros/[Nome_do_Livro]"`
2. Crie o arquivo `info.md` com:
```markdown
# Informações do Livro
**Título:** [Nome do Livro]
**Autor:** [Nome do Autor]
**Gênero:** [Ex: Teologia, Literatura, Formação Humana]
**Tamanho:** [Padrão: 14x21cm | Bolso: 12,5x18cm]
**Fonte:** [Padrão: Libre Baskerville]
```

### 2. Definição do Escopo (Briefing)
Pergunte ao usuário sobre:
- O objetivo central do livro.
- O estilo de escrita desejado (invocando as skills de `escrita/`).
- Referenciais específicos de autores.

### 3. Planejamento de Capítulos
Crie um arquivo `estrutura.md` com o sumário planejado.

### 4. Produção de Conteúdo
Ative o `editorial_orchestrator` para iniciar a escrita.
- Utilize a skill de escrita correspondente para cada capítulo.
- Salve o texto bruto em `texto_original.md`.

### 5. Revisão e Ajuste
Passe o texto pelas skills de `revisao/`:
1. `revisor_gramatical` (Correção normativa).
2. `revisor_estilo` (Alinhamento com o tom desejado).
3. `revisor_estrutura` (Pacing e tamanho dos parágrafos).

### 6. Produção e Diagramação Automática
1. Garanta que o texto final esteja em `texto_final.md`.
2. Configure as imagens na pasta `templates/assets/`.
3. Gere o PDF final executando o sistema centralizado:
// turbo
```bash
python3 3-layout/main.py texto_final.md --title "[Título]" --author "[Autor]" --output "output/[Nome_do_Livro].pdf"
```

### 7. Verificação Final
1. O sistema validará automaticamente se as dimensões são A5 (148.5mm x 210mm).
2. Verifique se a numeração iniciou corretamente no Capítulo 1.
3. O Sumário (TOC) deve estar presente e clicável.

---
**Comando de atalho:** `/novo-livro [Nome do Livro]`