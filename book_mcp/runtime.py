"""Runtime testável e independente do SDK MCP."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from shared.db_engine import database_path
from shared.continuity_auditor import audit_book_continuity
from shared.knowledge_governance import create_knowledge_proposal
from shared.operational_auditor import audit_book_invariants
from shared.embedding_engine import (
    DEFAULT_DIMENSIONS,
    DEFAULT_FASTEMBED_MODEL,
    FastEmbedAdapter,
)
from shared.entity_service import get_entity_dossier
from shared.inspection_service import get_scene_context, verify_book_index
from shared.search_service import SearchMode, search_book_context


@dataclass(frozen=True, slots=True)
class BookMCPConfig:
    db_path: Path
    default_search_mode: SearchMode = "lexical"
    embedding_model: str = DEFAULT_FASTEMBED_MODEL
    embedding_dimensions: int = DEFAULT_DIMENSIONS
    local_files_only: bool = True
    max_search_results: int = 20
    max_dossier_items: int = 100

    def __post_init__(self) -> None:
        if self.max_search_results < 1 or self.max_search_results > 100:
            raise ValueError("max_search_results deve estar entre 1 e 100")
        if self.max_dossier_items < 1 or self.max_dossier_items > 1_000:
            raise ValueError("max_dossier_items deve estar entre 1 e 1000")

    @classmethod
    def from_environment(cls) -> "BookMCPConfig":
        explicit_db = os.environ.get("BOOK_MCP_DB_PATH")
        book_dir = os.environ.get("BOOK_MCP_BOOK_DIR")
        if explicit_db:
            path = Path(explicit_db).expanduser().resolve()
        elif book_dir:
            path = database_path(book_dir)
        else:
            # Configuração é validada antes da primeira ferramenta; manter um
            # path sentinela permite que `mcp dev` importe o módulo.
            path = Path(".__book_mcp_not_configured__").resolve()
        mode = os.environ.get("BOOK_MCP_SEARCH_MODE", "lexical")
        if mode not in {"lexical", "semantic", "hybrid"}:
            raise ValueError(f"BOOK_MCP_SEARCH_MODE inválido: {mode}")
        return cls(
            db_path=path,
            default_search_mode=mode,  # type: ignore[arg-type]
            embedding_model=os.environ.get(
                "BOOK_MCP_EMBEDDING_MODEL", DEFAULT_FASTEMBED_MODEL
            ),
            embedding_dimensions=int(
                os.environ.get("BOOK_MCP_EMBEDDING_DIMENSIONS", DEFAULT_DIMENSIONS)
            ),
            local_files_only=os.environ.get("BOOK_MCP_LOCAL_FILES_ONLY", "1") != "0",
            max_search_results=int(os.environ.get("BOOK_MCP_MAX_SEARCH_RESULTS", "20")),
            max_dossier_items=int(os.environ.get("BOOK_MCP_MAX_DOSSIER_ITEMS", "100")),
        )


class BookRuntime:
    def __init__(self, config: BookMCPConfig) -> None:
        self.config = config
        self._embedder: FastEmbedAdapter | None = None

    def _require_database(self) -> Path:
        path = self.config.db_path
        if not path.is_file():
            raise FileNotFoundError(
                "book-mcp não configurado ou índice inexistente; defina "
                "BOOK_MCP_BOOK_DIR ou BOOK_MCP_DB_PATH"
            )
        return path

    def _semantic_dependencies(self):
        if self._embedder is None:
            self._embedder = FastEmbedAdapter(
                self.config.embedding_model,
                dimensions=self.config.embedding_dimensions,
                local_files_only=self.config.local_files_only,
            )
        try:
            import sqlite_vec
        except ImportError as exc:
            raise RuntimeError("instale 'sqlite-vec' para busca semântica") from exc
        return self._embedder, sqlite_vec.load

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        mode: SearchMode | None = None,
    ) -> list[dict[str, object]]:
        effective_mode = mode or self.config.default_search_mode
        limit = max(1, min(limit, self.config.max_search_results))
        kwargs: dict[str, object] = {}
        if effective_mode in {"semantic", "hybrid"}:
            embedder, loader = self._semantic_dependencies()
            kwargs.update(embedder=embedder, vector_loader=loader)
        return [
            hit.to_dict()
            for hit in search_book_context(
                self._require_database(),
                query,
                limit=limit,
                mode=effective_mode,
                **kwargs,  # type: ignore[arg-type]
            )
        ]

    def entity_dossier(
        self, entity_name: str, *, up_to_scene_uid: str | None = None
    ) -> dict[str, object]:
        dossier = get_entity_dossier(
            self._require_database(),
            entity_name,
            up_to_scene_uid=up_to_scene_uid,
        )
        truncated: dict[str, int] = {}
        for key in ("mentions", "relationships", "state_timeline", "claims"):
            items = dossier.get(key)
            if isinstance(items, list) and len(items) > self.config.max_dossier_items:
                truncated[key] = len(items) - self.config.max_dossier_items
                dossier[key] = items[: self.config.max_dossier_items]
        if truncated:
            dossier["truncated"] = truncated
        return dossier

    def scene_context(self, scene_uid: str) -> dict[str, object]:
        return get_scene_context(self._require_database(), scene_uid)

    def verify(self) -> dict[str, object]:
        return verify_book_index(self._require_database())

    def audit_continuity(self) -> list[dict[str, object]]:
        return [
            {
                "code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "evidence": issue.evidence,
            }
            for issue in audit_book_continuity(self._require_database())
        ]

    def audit_health(self) -> list[dict[str, object]]:
        return [
            {
                "code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "owner": issue.owner,
            }
            for issue in audit_book_invariants(self._require_database())
        ]

    def propose_knowledge(
        self,
        *,
        kind: str,
        payload: dict[str, object],
        source_scene_uid: str | None,
        source_excerpt: str | None,
        confidence: float,
    ) -> dict[str, object]:
        proposal = create_knowledge_proposal(
            self._require_database(),
            kind=kind,
            payload=payload,
            extraction_method="mcp-agent",
            source_scene_uid=source_scene_uid,
            source_excerpt=source_excerpt,
            confidence=confidence,
        )
        return {
            "proposal_uid": proposal.proposal_uid,
            "kind": proposal.kind,
            "status": proposal.status,
        }
