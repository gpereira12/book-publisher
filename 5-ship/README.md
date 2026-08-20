# 🚀 Ship — Projeto 5 (QA Pre-Flight & Validação Final)

**Status: a iniciar.** Ainda não há código neste módulo.

Este projeto será o portão de qualidade final antes de um livro ir para a gráfica ou loja digital. Ele recebe os entregáveis gerados pelo Layout (Projeto 3) e pelo Cover (Projeto 4) — PDF de impressão, PDF digital, EPUB3 e capa gráfica — e valida:

- **PDF/X compliance** para o arquivo de impressão (perfil de cor, caixas de sangria/corte).
- **CMYK** em vez de RGB nas artes de impressão (miolo e capa).
- **300 DPI** mínimo em todas as imagens embutidas.
- **Fontes embutidas** (embedding) no PDF final.
- **EPUBCheck** (conformidade com a especificação EPUB3) no arquivo digital.
- **Empacotamento**: gera o `.zip` de distribuição final com todos os entregáveis aprovados.

## Fronteira com o EPUB ilustrado

O módulo responsável por **gerar** o EPUB, inclusive a futura variante ilustrada
e responsiva, pertence ao Projeto 3 — Layout. Esta etapa de Ship não deve montar
ou reorganizar capítulos, textos e imagens.

Ao receber o EPUB ilustrado pronto, o Ship deverá validar:

- conformidade estrutural com EPUBCheck;
- presença de capa, sumário navegável e metadados;
- ordem de leitura e funcionamento dos links;
- textos alternativos e requisitos básicos de acessibilidade;
- integridade, formato, dimensões e peso das imagens incorporadas;
- ausência de números fixos de página ou dependência da geometria do PDF;
- abertura do arquivo em leitores representativos antes do empacotamento final.

**Pendência registrada:** implementar primeiro o módulo EPUB3 ilustrado no Layout
e, depois, criar aqui o portão automatizado de validação correspondente.

## Dependências ainda não presentes no `requirements.txt`

Nenhuma biblioteca de validação (`pikepdf`, `PyMuPDF`/`fitz`, wrapper de `epubcheck`) está instalada hoje — esse é o primeiro passo de implementação deste módulo.
