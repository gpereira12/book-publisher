"""Materialização incremental de embeddings locais em sqlite-vec."""

from __future__ import annotations

import argparse
import json
import sqlite3
import struct
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from shared.db_engine import connect, database_path, transaction
from shared.merkle import hash_node
from shared.sync_engine import _upsert_derivation_status


DEFAULT_FASTEMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_DIMENSIONS = 384


class DocumentEmbedder(Protocol):
    model_code: str
    model_name: str
    dimensions: int
    config_hash: str

    def embed_documents(self, texts: Sequence[str]) -> Iterable[Sequence[float]]: ...

    def embed_query(self, text: str) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class EmbeddingReport:
    database_path: str
    model_code: str
    dimensions: int
    total_passages: int
    embedded_passages: int
    cache_hits: int
    unchanged_passages: int
    rebuilt_index: bool


class FastEmbedAdapter:
    """Adaptador opcional para FastEmbed/ONNX, sem import obrigatório no core."""

    def __init__(
        self,
        model_name: str = DEFAULT_FASTEMBED_MODEL,
        *,
        dimensions: int = DEFAULT_DIMENSIONS,
        local_files_only: bool = False,
    ) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError("instale 'fastembed' para gerar embeddings") from exc
        self.model_name = model_name
        self.model_code = f"fastembed:{model_name}"
        self.dimensions = dimensions
        self.config_hash = hash_node(
            "embedding-model-config", self.model_code, dimensions
        )
        self._model = TextEmbedding(
            model_name=model_name,
            local_files_only=local_files_only,
        )

    def embed_documents(self, texts: Sequence[str]) -> Iterable[Sequence[float]]:
        return self._model.embed(list(texts))

    def embed_query(self, text: str) -> Sequence[float]:
        return next(iter(self._model.embed([text])))


VectorLoader = Callable[[sqlite3.Connection], None]
VectorInitializer = Callable[[sqlite3.Connection, int, VectorLoader, bool], None]


def _default_vector_initializer(
    connection: sqlite3.Connection,
    dimensions: int,
    loader: VectorLoader,
    rebuild: bool,
) -> None:
    try:
        connection.enable_load_extension(True)
    except AttributeError as exc:
        raise RuntimeError("este SQLite não permite carregar sqlite-vec") from exc
    try:
        loader(connection)
    finally:
        connection.enable_load_extension(False)
    if rebuild:
        connection.execute("DROP TABLE IF EXISTS passage_vectors")
    connection.execute(
        f"""CREATE VIRTUAL TABLE IF NOT EXISTS passage_vectors USING vec0(
                passage_id INTEGER PRIMARY KEY,
                embedding FLOAT[{int(dimensions)}] DISTANCE_METRIC=cosine
            )"""
    )


def _active_passages(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """WITH candidates AS (
               SELECT assignment.document_id, role.context_priority,
                      max(role.context_priority) OVER () AS selected_priority
               FROM edition_document_assignments AS assignment
               JOIN document_roles AS role ON role.id = assignment.document_role_id
               WHERE assignment.is_active = 1 AND role.is_manuscript = 1
           )
           SELECT passage.id, passage.scene_id, passage.content,
                  passage.content_sha256, root.root_hash AS content_merkle_root
           FROM candidates
           JOIN chapters AS chapter ON chapter.document_id = candidates.document_id
           JOIN scenes AS scene ON scene.chapter_id = chapter.id
           JOIN passages AS passage ON passage.scene_id = scene.id
           JOIN passage_merkle_roots AS root ON root.passage_id = passage.id
           JOIN merkle_root_kinds AS kind
                ON kind.id = root.root_kind_id AND kind.code = 'content'
           WHERE candidates.context_priority = candidates.selected_priority
           ORDER BY passage.id"""
    ).fetchall()


def _pack_vector(vector: Sequence[float], dimensions: int) -> bytes:
    values = [float(value) for value in vector]
    if len(values) != dimensions:
        raise ValueError(
            f"embedding possui {len(values)} dimensões; esperado: {dimensions}"
        )
    return struct.pack(f"<{dimensions}f", *values)


def materialize_embeddings(
    db_path: str | Path,
    *,
    embedder: DocumentEmbedder,
    vector_loader: VectorLoader,
    batch_size: int = 64,
    vector_initializer: VectorInitializer = _default_vector_initializer,
) -> EmbeddingReport:
    """Gera/reutiliza embeddings somente para passages do documento ativo."""

    if batch_size <= 0:
        raise ValueError("batch_size deve ser positivo")
    connection = connect(db_path)
    try:
        with transaction(connection):
            connection.execute(
                """INSERT INTO embedding_models(
                       code, model_name, dimensions, distance_metric, config_hash
                   ) VALUES (?, ?, ?, 'cosine', ?)
                   ON CONFLICT(code) DO UPDATE SET
                       model_name = excluded.model_name,
                       dimensions = excluded.dimensions,
                       distance_metric = excluded.distance_metric,
                       config_hash = excluded.config_hash""",
                (
                    embedder.model_code,
                    embedder.model_name,
                    embedder.dimensions,
                    embedder.config_hash,
                ),
            )
        model_id = connection.execute(
            "SELECT id FROM embedding_models WHERE code = ?", (embedder.model_code,)
        ).fetchone()[0]
        state = connection.execute(
            "SELECT model_id, dimensions, config_hash FROM vector_index_state WHERE id = 1"
        ).fetchone()
        rebuilt = state is None or (
            state["model_id"] != model_id
            or state["dimensions"] != embedder.dimensions
            or state["config_hash"] != embedder.config_hash
        )
        vector_initializer(
            connection, embedder.dimensions, vector_loader, rebuilt
        )
        with transaction(connection):
            if rebuilt:
                connection.execute("DELETE FROM passage_embedding_sources")
            connection.execute(
                """INSERT INTO vector_index_state(
                       id, model_id, dimensions, config_hash
                   ) VALUES (1, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       model_id = excluded.model_id,
                       dimensions = excluded.dimensions,
                       config_hash = excluded.config_hash,
                       rebuilt_at = CURRENT_TIMESTAMP""",
                (model_id, embedder.dimensions, embedder.config_hash),
            )

        passages = _active_passages(connection)
        existing_vector_ids = {
            row[0] for row in connection.execute("SELECT passage_id FROM passage_vectors")
        }
        sources = {
            row["passage_id"]: row["content_sha256"]
            for row in connection.execute(
                """SELECT passage_id, content_sha256
                   FROM passage_embedding_sources WHERE model_id = ?""",
                (model_id,),
            )
        }
        pending = [
            row
            for row in passages
            if row["id"] not in existing_vector_ids
            or sources.get(row["id"]) != row["content_sha256"]
        ]
        unchanged = len(passages) - len(pending)
        embedded = cache_hits = 0

        for offset in range(0, len(pending), batch_size):
            batch = pending[offset : offset + batch_size]
            resolved: dict[int, bytes] = {}
            missing_by_root: dict[str, sqlite3.Row] = {}
            for row in batch:
                cached = connection.execute(
                    """SELECT embedding FROM embedding_cache
                       WHERE model_id = ? AND content_merkle_root = ?""",
                    (model_id, row["content_merkle_root"]),
                ).fetchone()
                if cached is None:
                    missing_by_root.setdefault(row["content_merkle_root"], row)
                else:
                    resolved[row["id"]] = cached["embedding"]
                    cache_hits += 1

            if missing_by_root:
                missing = list(missing_by_root.values())
                vectors = list(
                    embedder.embed_documents([row["content"] for row in missing])
                )
                if len(vectors) != len(missing):
                    raise RuntimeError("embedder devolveu quantidade incorreta de vetores")
                vectors_by_root: dict[str, bytes] = {}
                for row, vector in zip(missing, vectors, strict=True):
                    vectors_by_root[row["content_merkle_root"]] = _pack_vector(
                        vector, embedder.dimensions
                    )
                    embedded += 1
                for row in batch:
                    if row["id"] not in resolved:
                        resolved[row["id"]] = vectors_by_root[
                            row["content_merkle_root"]
                        ]

            with transaction(connection):
                for row in batch:
                    # Uma sincronização concorrente pode ter alterado o passage.
                    current = connection.execute(
                        "SELECT content_sha256 FROM passages WHERE id = ?", (row["id"],)
                    ).fetchone()
                    if current is None or current["content_sha256"] != row["content_sha256"]:
                        continue
                    blob = resolved[row["id"]]
                    connection.execute(
                        "INSERT OR REPLACE INTO passage_vectors(passage_id, embedding) VALUES (?, ?)",
                        (row["id"], blob),
                    )
                    connection.execute(
                        """INSERT INTO embedding_cache(
                               model_id, content_merkle_root, dimensions, embedding
                           ) VALUES (?, ?, ?, ?)
                           ON CONFLICT(model_id, content_merkle_root) DO UPDATE SET
                               embedding = excluded.embedding,
                               dimensions = excluded.dimensions,
                               last_used_at = CURRENT_TIMESTAMP""",
                        (
                            model_id,
                            row["content_merkle_root"],
                            embedder.dimensions,
                            blob,
                        ),
                    )
                    connection.execute(
                        """INSERT INTO passage_embedding_sources(
                               passage_id, model_id, content_sha256
                           ) VALUES (?, ?, ?)
                           ON CONFLICT(passage_id, model_id) DO UPDATE SET
                               content_sha256 = excluded.content_sha256,
                               embedded_at = CURRENT_TIMESTAMP""",
                        (row["id"], model_id, row["content_sha256"]),
                    )

        scene_ids = sorted({row["scene_id"] for row in passages})
        with transaction(connection):
            for scene_id in scene_ids:
                scene = connection.execute(
                    "SELECT content_sha256 FROM scenes WHERE id = ?", (scene_id,)
                ).fetchone()
                missing_count = connection.execute(
                    """SELECT count(*) FROM passages AS passage
                       LEFT JOIN passage_embedding_sources AS source
                         ON source.passage_id = passage.id AND source.model_id = ?
                        AND source.content_sha256 = passage.content_sha256
                       WHERE passage.scene_id = ? AND source.passage_id IS NULL""",
                    (model_id, scene_id),
                ).fetchone()[0]
                _upsert_derivation_status(
                    connection,
                    scene_id,
                    "embeddings",
                    "fresh" if missing_count == 0 else "pending",
                    scene["content_sha256"],
                    generated=missing_count == 0,
                )
        return EmbeddingReport(
            database_path=str(Path(db_path).resolve()),
            model_code=embedder.model_code,
            dimensions=embedder.dimensions,
            total_passages=len(passages),
            embedded_passages=embedded,
            cache_hits=cache_hits,
            unchanged_passages=unchanged,
            rebuilt_index=rebuilt,
        )
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Materializa embeddings locais do livro")
    parser.add_argument("book_dir")
    parser.add_argument("--model", default=DEFAULT_FASTEMBED_MODEL)
    parser.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        import sqlite_vec
    except ImportError as exc:
        raise SystemExit("instale 'sqlite-vec' para criar o índice vetorial") from exc
    embedder = FastEmbedAdapter(
        args.model,
        dimensions=args.dimensions,
        local_files_only=args.local_files_only,
    )
    report = materialize_embeddings(
        database_path(Path(args.book_dir).resolve()),
        embedder=embedder,
        vector_loader=sqlite_vec.load,
        batch_size=args.batch_size,
    )
    payload = asdict(report)
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload)


if __name__ == "__main__":
    main()
