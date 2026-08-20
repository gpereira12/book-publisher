from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from shared.db_engine import connect, transaction
from shared.embedding_engine import materialize_embeddings
from shared.merkle import hash_node
from shared.sync_engine import sync_book


class FakeEmbedder:
    model_code = "fake:deterministic-v1"
    model_name = "Fake Deterministic"
    dimensions = 4
    config_hash = hash_node("fake-model", model_code, dimensions)

    def __init__(self) -> None:
        self.document_calls = 0

    def _vector(self, text: str) -> list[float]:
        base = float(sum(ord(character) for character in text) % 97) / 97.0
        return [base, base / 2, 1.0 - base, 0.25]

    def embed_documents(self, texts: list[str]):
        self.document_calls += len(texts)
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str):
        return self._vector(text)


def fake_vector_initializer(connection, dimensions, loader, rebuild):
    if rebuild:
        connection.execute("DROP TABLE IF EXISTS passage_vectors")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS passage_vectors(
               passage_id INTEGER PRIMARY KEY,
               embedding BLOB NOT NULL
           )"""
    )


class EmbeddingEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.temp_dir.name) / "livro"
        self.book_dir.mkdir()
        (self.book_dir / "texto_original.md").write_text(
            "# Um\n\nPrimeiro parágrafo.\n\nSegundo parágrafo.\n",
            encoding="utf-8",
        )
        self.sync_report = sync_book(
            self.book_dir,
            passage_target_words=2,
            passage_overlap_paragraphs=0,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_incremental_embeddings_and_content_cache(self) -> None:
        embedder = FakeEmbedder()
        first = materialize_embeddings(
            self.sync_report.database_path,
            embedder=embedder,
            vector_loader=lambda connection: None,
            vector_initializer=fake_vector_initializer,
        )
        self.assertTrue(first.rebuilt_index)
        self.assertEqual(first.total_passages, first.embedded_passages)

        second = materialize_embeddings(
            self.sync_report.database_path,
            embedder=embedder,
            vector_loader=lambda connection: None,
            vector_initializer=fake_vector_initializer,
        )
        self.assertFalse(second.rebuilt_index)
        self.assertEqual(first.total_passages, second.unchanged_passages)

        connection = connect(self.sync_report.database_path)
        try:
            passage_id = connection.execute(
                "SELECT passage_id FROM passage_vectors ORDER BY passage_id LIMIT 1"
            ).fetchone()[0]
            with transaction(connection):
                connection.execute(
                    "DELETE FROM passage_vectors WHERE passage_id = ?", (passage_id,)
                )
                connection.execute(
                    "DELETE FROM passage_embedding_sources WHERE passage_id = ?",
                    (passage_id,),
                )
        finally:
            connection.close()

        calls_before_cache = embedder.document_calls
        third = materialize_embeddings(
            self.sync_report.database_path,
            embedder=embedder,
            vector_loader=lambda connection: None,
            vector_initializer=fake_vector_initializer,
        )
        self.assertEqual(1, third.cache_hits)
        self.assertEqual(calls_before_cache, embedder.document_calls)


if __name__ == "__main__":
    unittest.main()
