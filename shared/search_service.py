"""Busca lexical, semântica e híbrida sobre passages do livro ativo."""

from __future__ import annotations

import re
import sqlite3
import struct
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Protocol

from shared.db_engine import connect


SearchMode = Literal["lexical", "semantic", "hybrid"]


class SearchUnavailableError(RuntimeError):
    """A modalidade solicitada não está materializada ou configurada."""


class QueryEmbedder(Protocol):
    def embed_query(self, text: str) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class SearchHit:
    passage_id: int
    scene_uid: str
    scene_title: str | None
    chapter_uid: str
    chapter_title: str | None
    document_path: str
    start_line: int
    end_line: int
    content: str
    snippet: str | None
    score: float
    lexical_rank: int | None
    semantic_rank: int | None
    lexical_score: float | None
    semantic_distance: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def active_document_ids(connection: sqlite3.Connection) -> list[int]:
    """Seleciona todos os manuscritos ativos na maior prioridade editorial."""

    rows = connection.execute(
        """WITH candidates AS (
               SELECT assignment.document_id, role.context_priority,
                      max(role.context_priority) OVER () AS selected_priority
               FROM edition_document_assignments AS assignment
               JOIN document_roles AS role ON role.id = assignment.document_role_id
               WHERE assignment.is_active = 1 AND role.is_manuscript = 1
           )
           SELECT document_id FROM candidates
           WHERE context_priority = selected_priority ORDER BY document_id"""
    ).fetchall()
    if rows:
        return [row["document_id"] for row in rows]
    return [
        row["id"]
        for row in connection.execute(
            "SELECT id FROM documents WHERE kind = 'manuscript' ORDER BY id"
        )
    ]


def _safe_fts_query(text: str) -> str:
    terms = re.findall(r"[\wÀ-ÖØ-öø-ÿ]+", text, flags=re.UNICODE)
    if not terms:
        raise ValueError("a consulta precisa conter ao menos uma palavra")
    # OR aumenta recall; o ranking BM25 favorece passages com mais termos.
    return " OR ".join(f'"{term}"' for term in terms)


def _document_filter(document_ids: list[int], alias: str = "document") -> tuple[str, list[int]]:
    if not document_ids:
        return "0", []
    placeholders = ",".join("?" for _ in document_ids)
    return f"{alias}.id IN ({placeholders})", document_ids


def _lexical_rows(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int,
    document_ids: list[int],
) -> list[sqlite3.Row]:
    condition, params = _document_filter(document_ids)
    return connection.execute(
        f"""SELECT passage.id AS passage_id, scene.scene_uid,
                   scene.scene_title, chapter.chapter_uid,
                   chapter.title AS chapter_title,
                   document.relative_path AS document_path,
                   passage.start_line, passage.end_line, passage.content,
                   snippet(passage_fts, 0, '<mark>', '</mark>', ' … ', 24) AS snippet,
                   bm25(passage_fts) AS lexical_score
            FROM passage_fts
            JOIN passages AS passage ON passage.id = passage_fts.rowid
            JOIN scenes AS scene ON scene.id = passage.scene_id
            JOIN chapters AS chapter ON chapter.id = scene.chapter_id
            JOIN documents AS document ON document.id = chapter.document_id
            WHERE passage_fts MATCH ? AND {condition}
            ORDER BY lexical_score
            LIMIT ?""",
        [_safe_fts_query(query), *params, limit],
    ).fetchall()


def _load_vector_extension(
    connection: sqlite3.Connection,
    loader: Callable[[sqlite3.Connection], None],
) -> None:
    try:
        connection.enable_load_extension(True)
    except AttributeError as exc:
        raise SearchUnavailableError(
            "este build de SQLite não permite carregar sqlite-vec"
        ) from exc
    try:
        loader(connection)
    finally:
        connection.enable_load_extension(False)


def _semantic_rows(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int,
    document_ids: list[int],
    embedder: QueryEmbedder,
) -> tuple[list[sqlite3.Row], dict[int, float]]:
    state = connection.execute(
        "SELECT dimensions FROM vector_index_state WHERE id = 1"
    ).fetchone()
    if state is None:
        raise SearchUnavailableError("índice vetorial ainda não foi materializado")
    vector = [float(value) for value in embedder.embed_query(query)]
    if len(vector) != state["dimensions"]:
        raise SearchUnavailableError(
            f"consulta gerou {len(vector)} dimensões; índice usa {state['dimensions']}"
        )
    blob = struct.pack(f"<{len(vector)}f", *vector)
    candidates = connection.execute(
        """SELECT passage_id, distance FROM passage_vectors
           WHERE embedding MATCH ? AND k = ? ORDER BY distance""",
        (blob, max(limit * 5, limit)),
    ).fetchall()
    if not candidates or not document_ids:
        return [], {}
    candidate_ids = [row["passage_id"] for row in candidates]
    distances = {row["passage_id"]: row["distance"] for row in candidates}
    passage_placeholders = ",".join("?" for _ in candidate_ids)
    document_condition, document_params = _document_filter(document_ids)
    rows = connection.execute(
        f"""SELECT passage.id AS passage_id, scene.scene_uid,
                   scene.scene_title, chapter.chapter_uid,
                   chapter.title AS chapter_title,
                   document.relative_path AS document_path,
                   passage.start_line, passage.end_line, passage.content
            FROM passages AS passage
            JOIN scenes AS scene ON scene.id = passage.scene_id
            JOIN chapters AS chapter ON chapter.id = scene.chapter_id
            JOIN documents AS document ON document.id = chapter.document_id
            WHERE passage.id IN ({passage_placeholders}) AND {document_condition}""",
        [*candidate_ids, *document_params],
    ).fetchall()
    by_id = {row["passage_id"]: row for row in rows}
    ordered = [by_id[passage_id] for passage_id in candidate_ids if passage_id in by_id]
    # sqlite3.Row é imutável; a distância volta em um mapa separado no chamador.
    return ordered[:limit], distances


def search_book_context(
    db_path: str | Path,
    query: str,
    *,
    limit: int = 8,
    mode: SearchMode = "lexical",
    embedder: QueryEmbedder | None = None,
    vector_loader: Callable[[sqlite3.Connection], None] | None = None,
    rrf_k: int = 60,
    max_per_scene: int = 2,
) -> list[SearchHit]:
    """Busca passages do documento ativo e combina rankings por RRF."""

    if not 1 <= limit <= 100:
        raise ValueError("limit deve estar entre 1 e 100")
    if max_per_scene <= 0:
        raise ValueError("max_per_scene deve ser positivo")
    if mode not in {"lexical", "semantic", "hybrid"}:
        raise ValueError(f"modo de busca inválido: {mode}")
    connection = connect(db_path, read_only=True)
    try:
        document_ids = active_document_ids(connection)
        candidate_limit = min(400, max(limit * 4, limit))
        lexical = (
            _lexical_rows(
                connection, query, limit=candidate_limit, document_ids=document_ids
            )
            if mode in {"lexical", "hybrid"}
            else []
        )
        semantic: list[sqlite3.Row] = []
        distances: dict[int, float] = {}
        if mode in {"semantic", "hybrid"}:
            if embedder is None or vector_loader is None:
                raise SearchUnavailableError(
                    "busca semântica requer embedder e loader sqlite-vec"
                )
            _load_vector_extension(connection, vector_loader)
            semantic_result = _semantic_rows(
                connection,
                query,
                limit=candidate_limit,
                document_ids=document_ids,
                embedder=embedder,
            )
            semantic, distances = semantic_result

        lexical_rank = {
            row["passage_id"]: rank for rank, row in enumerate(lexical, start=1)
        }
        semantic_rank = {
            row["passage_id"]: rank for rank, row in enumerate(semantic, start=1)
        }
        lexical_scores = {
            row["passage_id"]: float(row["lexical_score"]) for row in lexical
        }
        metadata = {row["passage_id"]: row for row in [*lexical, *semantic]}
        scores: dict[int, float] = {}
        for passage_id, rank in lexical_rank.items():
            scores[passage_id] = scores.get(passage_id, 0.0) + 1.0 / (rrf_k + rank)
        for passage_id, rank in semantic_rank.items():
            scores[passage_id] = scores.get(passage_id, 0.0) + 1.0 / (rrf_k + rank)

        ordered_ids = sorted(scores, key=lambda item: (-scores[item], item))
        hits: list[SearchHit] = []
        per_scene: dict[str, int] = {}
        for passage_id in ordered_ids:
            row = metadata[passage_id]
            scene_uid = row["scene_uid"]
            if per_scene.get(scene_uid, 0) >= max_per_scene:
                continue
            per_scene[scene_uid] = per_scene.get(scene_uid, 0) + 1
            hits.append(
                SearchHit(
                    passage_id=passage_id,
                    scene_uid=scene_uid,
                    scene_title=row["scene_title"],
                    chapter_uid=row["chapter_uid"],
                    chapter_title=row["chapter_title"],
                    document_path=row["document_path"],
                    start_line=row["start_line"],
                    end_line=row["end_line"],
                    content=row["content"],
                    snippet=row["snippet"] if "snippet" in row.keys() else None,
                    score=scores[passage_id],
                    lexical_rank=lexical_rank.get(passage_id),
                    semantic_rank=semantic_rank.get(passage_id),
                    lexical_score=lexical_scores.get(passage_id),
                    semantic_distance=(
                        float(distances[passage_id]) if passage_id in distances else None
                    ),
                )
            )
            if len(hits) >= limit:
                break
        return hits
    finally:
        connection.close()
