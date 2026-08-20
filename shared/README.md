# Motor de conhecimento editorial

Os módulos desta pasta mantêm índices SQLite derivados. Markdown e YAML dentro
de `inputs/<livro>/` continuam sendo a fonte canônica versionada no Git.

## Sincronização

Por padrão, o Harness usa `texto_revisado.md` quando existe e, caso contrário,
`texto_original.md`:

```bash
python -m shared.sync_engine inputs/meu_livro
```

Para selecionar explicitamente a fonte e obter saída estruturada:

```bash
python -m shared.sync_engine inputs/meu_livro \
  --manuscript texto_original.md \
  --json
```

O papel editorial pode ser definido durante o sync:

```bash
python -m shared.sync_engine inputs/meu_livro \
  --manuscript texto_revisado.md \
  --document-role approved_manuscript
```

Papéis ativos têm prioridade: `approved_manuscript`, `working_revision`,
`translation` e `source_original`. Busca e roots da obra usam o manuscrito
ativo de maior prioridade, sem misturar original e revisão.

Opções relevantes:

- `--chapter-heading-level 1`: sobrescreve a detecção automática de capítulos;
- `--passage-target-words 350`: tamanho-alvo do chunk;
- `--passage-overlap-paragraphs 1`: sobreposição entre chunks.

Uma segunda execução com o mesmo SHA-256 e a mesma configuração do parser usa
o fast-path e não reprocessa cenas.

## Identidades persistentes

O parser aceita marcadores que não aparecem no livro renderizado:

```markdown
<!-- chapter:01JCHAPTER0000000000000001 title="A Travessia" -->
# A Travessia

<!-- scene:01JSCENE000000000000000001 title="A ponte" -->
Texto da cena.
```

IDs devem ter pelo menos 16 caracteres e nunca devem ser reutilizados. ULID,
UUID ou um identificador editorial longo funcionam. Sem marcador explícito, o
Harness tenta, nesta ordem:

1. reutilizar a chave estrutural anterior;
2. reconhecer conteúdo por SHA-256 único;
3. gerar UUID5 determinístico.

O título do capítulo fica fora do hash da cena implícita. Assim, renomear um
capítulo não invalida embeddings do corpo textual.

## Incrementalidade

Quando uma cena muda, o Harness:

1. grava um unified diff em `scene_revisions`;
2. atualiza a cena e os triggers FTS5;
3. atualiza somente seus passages;
4. preserva embeddings de passages cujo conteúdo não mudou;
5. marca menções, estados, achados, beats e embeddings afetados como stale ou
   pending em `scene_derivation_status`.

Consumidores devem consultar apenas materializações com status `fresh`.

Uma cena removida gera um tombstone em `scene_tombstones`; seus patches são
copiados para `archived_scene_revisions` antes do `CASCADE`. Divisões e fusões
podem ser registradas em `scene_lineage` sem reutilizar UIDs.

Cada execução usa um writer lease e deixa uma linha em `sync_attempts`, mesmo
quando a transação principal falha. Operações de recuperação:

```bash
python -m shared.reliability reconcile inputs/meu_livro
python -m shared.reliability rebuild inputs/meu_livro
```

O rebuild cria o novo banco em staging, valida o fechamento do WAL, salva um
backup e só então faz a troca atômica.

```bash
python -m shared.reliability verify-backup inputs/meu_livro/.book_index.db.backup-123
python -m shared.reliability restore inputs/meu_livro \
  inputs/meu_livro/.book_index.db.backup-123
python -m shared.reliability prune-backups inputs/meu_livro --keep 5
```

## Conhecimento YAML e universos

Entidades, aliases, relações, estados e claims aprovados podem ser ingeridos de
um `knowledge.yaml` ou de um dossiê com a chave `personagens`:

```bash
python -m shared.knowledge_sync inputs/meu_livro --yaml knowledge.yaml --json
```

Claims exigem `scene_uid`; assim, toda afirmação mantém proveniência textual.
As fontes de autoridade são ordenadas (`approved_canon`, `editorial_dossier`,
`manuscript_explicit`, `model_suggestion`) e a view `ranked_entity_claims`
expõe a precedência sem apagar divergências. Menções exatas são extraídas de
forma determinística usando nome e aliases.

### Contrato e governança

Novos arquivos devem declarar `schema_version: 1`. O contrato publicável está
em `shared/knowledge.schema.json`; a validação informa o caminho do campo
inválido. Dossiês legados com `personagens` continuam aceitos.

Predicados podem declarar `value_kind`, `cardinality`, `temporal_mode` e
`unit`. Claims aceitam `valid_from_scene_uid` e `valid_to_scene_uid`.

Sugestões automáticas entram como `suggested` e dependem de decisão humana para
virar `approved`, `rejected` ou `superseded`. Elas nunca criam silenciosamente
claims canônicos. Propostas, decisões e operações de merge/split são gravadas
em `knowledge_reviews.jsonl`, event log canônico encadeado por SHA-256 e
reconstruído durante rebuilds.

Merges mantêm redirects para UIDs antigos. Splits criam uma identidade nova e
preservam ator, justificativa e aliases transferidos.

Para agregar obras sem copiar o texto entre bancos:

```bash
python -m shared.universe_sync universos/meu_universo \
  --universe-uid urn:universe:meu-universo \
  --book inputs/livro_um --book inputs/livro_dois
```

Mapeamentos com `universe_uid` explícito têm confiança 1.0; correspondências
apenas por nome entram como `uncertain` e confiança 0.5, para revisão humana.

## Merkle DAG editorial

Cada sincronização calcula roots SHA-256 com separação de domínio e partes
prefixadas por tamanho:

- `content`: depende do texto e da ordem narrativa, não de títulos ou chunking;
- `structure`: depende de UIDs, títulos, ordem e composição;
- `materialization`: depende do conteúdo, parser e configuração de passages;
- `knowledge`: agrega entidades, aliases, relações, states, claims e proveniência.

Os roots existem em níveis de passage, cena, capítulo, documento e obra. O
relatório JSON do Harness devolve os três roots do documento, e `sync_runs`
preserva os roots de cada execução para auditoria.

Consequências esperadas:

- editar texto altera `content` e `materialization`;
- renomear capítulo altera somente `structure`;
- trocar chunking altera somente `materialization`;
- mudar uma relação ou claim altera `knowledge`.

O índice de universo importa apenas os quatro roots de cada obra. O texto
integral permanece no `.book_index.db` isolado.

## Embeddings locais

Depois do Harness Sync:

```bash
python -m shared.embedding_engine inputs/meu_livro --json
```

O padrão é o modelo multilíngue de 384 dimensões
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. O motor:

- processa somente passages do manuscrito ativo;
- reutiliza `embedding_cache` por model + content root;
- atualiza apenas passages alterados;
- mantém um único modelo vetorial ativo por banco;
- marca a materialização de embeddings como `fresh` ou `pending`.

Para impedir qualquer download durante a execução:

```bash
python -m shared.embedding_engine inputs/meu_livro --local-files-only
```

## Book MCP

O processo fica vinculado a um único banco no startup; nenhuma ferramenta
aceita caminhos arbitrários:

```bash
export BOOK_MCP_BOOK_DIR="inputs/meu_livro"
export BOOK_MCP_SEARCH_MODE="hybrid"
export BOOK_MCP_LOCAL_FILES_ONLY="1"
python -m book_mcp.server
```

Ferramentas expostas:

- `search_book_context`;
- `get_entity_dossier`;
- `get_scene_context`;
- `verify_book_index`.
- `audit_book_continuity`.
- `audit_book_health`;
- `propose_book_knowledge` (fila de revisão, sem promoção automática).

Resultados possuem limites configuráveis por `BOOK_MCP_MAX_SEARCH_RESULTS` e
`BOOK_MCP_MAX_DOSSIER_ITEMS`. O ambiente opcional pode ser diagnosticado sem
downloads:

```bash
python -m shared.stack_diagnostics
```

Busca `semantic` e `hybrid` requerem que o índice vetorial tenha sido
materializado. Busca `lexical` funciona somente com SQLite/FTS5.

## Bancos

- `db_engine.py`: `.book_index.db`, isolado por livro;
- `universe_db_engine.py`: `.universe_index.db`, identidades e relações entre obras;
- `markdown_scene_parser.py`: segmentação sem mutação do Markdown;
- `sync_engine.py`: sincronização transacional e incremental.
- `merkle.py`: hashing por domínio e propagação de roots.
- `search_service.py`: BM25, sqlite-vec e Reciprocal Rank Fusion;
- `entity_service.py`: dossiê e state timeline;
- `embedding_engine.py`: FastEmbed incremental e cache vetorial;
- `inspection_service.py`: cenas e diagnóstico do índice.
- `reliability.py`: leases, tentativas, reconciliação, linhagem e rebuild atômico;
- `knowledge_sync.py`: ingestão YAML, aliases, menções, estados e claims;
- `universe_sync.py`: agregação de roots e identidades entre obras;
- `continuity_auditor.py`: conflitos de claims e ciclos cronológicos.
- `knowledge_contract.py` / `knowledge.schema.json`: contrato YAML v1;
- `knowledge_governance.py`: propostas, decisões e log canônico encadeado;
- `entity_identity.py`: merge, split e redirects auditáveis;
- `operational_auditor.py`: fontes, anchors, hashes, FKs e materializações;
- `stack_diagnostics.py`: diagnóstico offline das dependências opcionais.
