"""Servidor MCP v2, stdio por padrão, vinculado a um único índice local."""

from __future__ import annotations

import asyncio

from book_mcp.runtime import BookMCPConfig, BookRuntime

try:
    from mcp.server import MCPServer
except ImportError as exc:  # pragma: no cover - depende do pacote opcional
    MCPServer = None  # type: ignore[assignment,misc]
    _MCP_IMPORT_ERROR = exc
else:
    _MCP_IMPORT_ERROR = None


def create_server(config: BookMCPConfig | None = None):
    if MCPServer is None:
        raise RuntimeError("instale 'mcp[cli]>=2,<3' para executar book-mcp") from _MCP_IMPORT_ERROR
    runtime = BookRuntime(config or BookMCPConfig.from_environment())
    server = MCPServer(
        "book-mcp",
        instructions=(
            "Consulta somente o índice editorial configurado no startup. "
            "Resultados incluem UIDs, arquivo e linhas para rastreabilidade."
        ),
    )

    @server.tool()
    async def search_book_context(
        query: str,
        limit: int = 8,
        mode: str | None = None,
    ) -> list[dict[str, object]]:
        """Busca contexto no manuscrito ativo por FTS, vetores ou modo híbrido."""

        if mode is not None and mode not in {"lexical", "semantic", "hybrid"}:
            raise ValueError("mode deve ser lexical, semantic ou hybrid")
        return await asyncio.to_thread(
            runtime.search,
            query,
            limit=limit,
            mode=mode,
        )

    @server.tool()
    async def get_entity_dossier(
        entity_name: str,
        up_to_scene_uid: str | None = None,
    ) -> dict[str, object]:
        """Retorna identidade, aliases, relações, claims e estados da entidade."""

        return await asyncio.to_thread(
            runtime.entity_dossier,
            entity_name,
            up_to_scene_uid=up_to_scene_uid,
        )

    @server.tool()
    async def get_scene_context(scene_uid: str) -> dict[str, object]:
        """Retorna texto, âncoras, conexões e estado das materializações da cena."""

        return await asyncio.to_thread(runtime.scene_context, scene_uid)

    @server.tool()
    async def verify_book_index() -> dict[str, object]:
        """Verifica integridade, roots Merkle e materializações do índice."""

        return await asyncio.to_thread(runtime.verify)

    @server.tool()
    async def audit_book_continuity() -> list[dict[str, object]]:
        """Detecta claims de mesma autoridade que contradizem a continuidade."""

        return await asyncio.to_thread(runtime.audit_continuity)

    @server.tool()
    async def audit_book_health() -> list[dict[str, object]]:
        """Audita fontes, hashes, anchors, FKs, roots e materializações."""

        return await asyncio.to_thread(runtime.audit_health)

    @server.tool()
    async def propose_book_knowledge(
        kind: str,
        payload: dict[str, object],
        source_scene_uid: str | None = None,
        source_excerpt: str | None = None,
        confidence: float = 1.0,
    ) -> dict[str, object]:
        """Registra sugestão isolada; nunca promove conhecimento sem revisão humana."""

        return await asyncio.to_thread(
            runtime.propose_knowledge,
            kind=kind,
            payload=payload,
            source_scene_uid=source_scene_uid,
            source_excerpt=source_excerpt,
            confidence=confidence,
        )

    return server


mcp = create_server() if MCPServer is not None else None


def main() -> None:
    server = mcp or create_server()
    server.run()  # stdio é o transporte local padrão


if __name__ == "__main__":
    main()
