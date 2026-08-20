# book-mcp

Servidor MCP local vinculado a um único `.book_index.db`.

## Configuração

Defina uma destas variáveis:

```bash
export BOOK_MCP_BOOK_DIR="/caminho/inputs/meu_livro"
# ou
export BOOK_MCP_DB_PATH="/caminho/inputs/meu_livro/.book_index.db"
```

Configuração opcional:

```bash
export BOOK_MCP_SEARCH_MODE="lexical" # lexical, semantic ou hybrid
export BOOK_MCP_EMBEDDING_MODEL="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
export BOOK_MCP_EMBEDDING_DIMENSIONS="384"
export BOOK_MCP_LOCAL_FILES_ONLY="1"
export BOOK_MCP_MAX_SEARCH_RESULTS="20"
export BOOK_MCP_MAX_DOSSIER_ITEMS="100"
```

`BOOK_MCP_LOCAL_FILES_ONLY=1` é o padrão para impedir downloads durante uma
sessão MCP.

## Execução

```bash
python -m book_mcp.server
```

O transporte padrão é stdio. Logs e diagnósticos não devem ser escritos em
stdout, pois stdout pertence ao protocolo.

Ferramentas:

- `search_book_context`;
- `get_entity_dossier`;
- `get_scene_context`;
- `verify_book_index`;
- `audit_book_continuity`;
- `audit_book_health`;
- `propose_book_knowledge`, que apenas cria uma proposta revisável.
