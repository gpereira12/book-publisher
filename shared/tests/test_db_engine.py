from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from shared.db_engine import (
    LATEST_SCHEMA_VERSION,
    MIGRATION_001,
    connect,
    initialize_book_database,
    migrate,
    transaction,
    verify_integrity,
)


class DatabaseEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.temp_dir.name) / "meu_livro"
        self.book_dir.mkdir()
        self.db_path = initialize_book_database(
            self.book_dir, slug="meu_livro", title="Meu Livro"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initialization_is_idempotent_and_uses_wal(self) -> None:
        initialize_book_database(self.book_dir, title="Meu Livro — edição 2")
        connection = connect(self.db_path)
        try:
            self.assertEqual(
                LATEST_SCHEMA_VERSION,
                connection.execute("PRAGMA user_version").fetchone()[0],
            )
            self.assertEqual(
                "wal", connection.execute("PRAGMA journal_mode").fetchone()[0].lower()
            )
            self.assertEqual(
                "Meu Livro — edição 2",
                connection.execute("SELECT title FROM books WHERE id = 1").fetchone()[0],
            )
            self.assertEqual(
                7, connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
            )
            self.assertEqual(1, connection.execute("SELECT count(*) FROM works").fetchone()[0])
            self.assertEqual(1, connection.execute("SELECT count(*) FROM editions").fetchone()[0])
            verify_integrity(connection)
        finally:
            connection.close()

    def test_scene_triggers_keep_fts_in_sync(self) -> None:
        content = "A sentinela encontrou a chave de jade."
        digest = hashlib.sha256(content.encode()).hexdigest()
        connection = connect(self.db_path)
        try:
            with transaction(connection):
                document_id = connection.execute(
                    "INSERT INTO documents(book_id, kind, relative_path) VALUES (1, 'manuscript', 'texto.md')"
                ).lastrowid
                chapter_id = connection.execute(
                    """INSERT INTO chapters(
                           document_id, ordinal, stable_key, chapter_uid, title, start_line, end_line
                       ) VALUES (?, 0, 'capitulo-1', '01JCHAPTER0000000000000001', 'Capítulo 1', 1, 3)""",
                    (document_id,),
                ).lastrowid
                scene_id = connection.execute(
                    """INSERT INTO scenes(
                           chapter_id, ordinal, stable_key, scene_uid, scene_title,
                           start_line, end_line, content, content_sha256
                       ) VALUES (?, 0, 'cena-1', '01JSCENE000000000000000001',
                                 'O achado', 2, 3, ?, ?)""",
                    (chapter_id, content, digest),
                ).lastrowid

            result = connection.execute(
                "SELECT rowid FROM scene_fts WHERE scene_fts MATCH ?", ('"jade"',)
            ).fetchone()
            self.assertEqual(scene_id, result[0])

            with transaction(connection):
                connection.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
            self.assertIsNone(
                connection.execute(
                    "SELECT rowid FROM scene_fts WHERE scene_fts MATCH ?", ('"jade"',)
                ).fetchone()
            )
        finally:
            connection.close()

    def test_passage_fts_is_independent_from_scene_granularity(self) -> None:
        scene_content = "A sentinela encontrou a chave. Depois atravessou a ponte."
        passage_content = "Depois atravessou a ponte."
        connection = connect(self.db_path)
        try:
            with transaction(connection):
                document_id = connection.execute(
                    "INSERT INTO documents(book_id, kind, relative_path) VALUES (1, 'manuscript', 'texto.md')"
                ).lastrowid
                chapter_id = connection.execute(
                    """INSERT INTO chapters(
                           document_id, ordinal, stable_key, chapter_uid, title, start_line, end_line
                       ) VALUES (?, 0, 'capitulo-1', '01JCHAPTER0000000000000002', 'Capítulo 1', 1, 3)""",
                    (document_id,),
                ).lastrowid
                scene_id = connection.execute(
                    """INSERT INTO scenes(
                           chapter_id, ordinal, stable_key, scene_uid, scene_title,
                           start_line, end_line, content, content_sha256
                       ) VALUES (?, 0, 'cena-1', '01JSCENE000000000000000002',
                                 'Travessia', 2, 3, ?, ?)""",
                    (
                        chapter_id,
                        scene_content,
                        hashlib.sha256(scene_content.encode()).hexdigest(),
                    ),
                ).lastrowid
                passage_id = connection.execute(
                    """INSERT INTO passages(
                           scene_id, ordinal, start_offset, end_offset, start_line,
                           end_line, content, content_sha256
                       ) VALUES (?, 0, 30, 56, 3, 3, ?, ?)""",
                    (
                        scene_id,
                        passage_content,
                        hashlib.sha256(passage_content.encode()).hexdigest(),
                    ),
                ).lastrowid

            hit = connection.execute(
                "SELECT rowid FROM passage_fts WHERE passage_fts MATCH ?",
                ('"ponte"',),
            ).fetchone()
            self.assertEqual(passage_id, hit[0])
        finally:
            connection.close()

    def test_scene_uid_survives_move_between_chapters(self) -> None:
        content = "Uma cena móvel."
        connection = connect(self.db_path)
        try:
            with transaction(connection):
                document_id = connection.execute(
                    "INSERT INTO documents(book_id, kind, relative_path) VALUES (1, 'manuscript', 'texto.md')"
                ).lastrowid
                first_chapter = connection.execute(
                    """INSERT INTO chapters(
                           document_id, ordinal, stable_key, chapter_uid, start_line, end_line
                       ) VALUES (?, 0, 'capitulo-1', '01JCHAPTER0000000000000003', 1, 3)""",
                    (document_id,),
                ).lastrowid
                second_chapter = connection.execute(
                    """INSERT INTO chapters(
                           document_id, ordinal, stable_key, chapter_uid, start_line, end_line
                       ) VALUES (?, 1, 'capitulo-2', '01JCHAPTER0000000000000004', 4, 6)""",
                    (document_id,),
                ).lastrowid
                scene_id = connection.execute(
                    """INSERT INTO scenes(
                           chapter_id, ordinal, stable_key, scene_uid,
                           start_line, end_line, content, content_sha256
                       ) VALUES (?, 0, 'cena-movel', '01JSCENE000000000000000003',
                                 2, 3, ?, ?)""",
                    (first_chapter, content, hashlib.sha256(content.encode()).hexdigest()),
                ).lastrowid
            with transaction(connection):
                connection.execute(
                    "UPDATE scenes SET chapter_id = ?, start_line = 5, end_line = 6 WHERE id = ?",
                    (second_chapter, scene_id),
                )
            moved = connection.execute(
                "SELECT id, scene_uid, chapter_id FROM scenes WHERE id = ?", (scene_id,)
            ).fetchone()
            self.assertEqual("01JSCENE000000000000000003", moved["scene_uid"])
            self.assertEqual(second_chapter, moved["chapter_id"])
        finally:
            connection.close()

    def test_v1_database_upgrades_and_backfills_scene_uid(self) -> None:
        legacy_dir = Path(self.temp_dir.name) / "legacy"
        legacy_dir.mkdir()
        legacy_db = legacy_dir / ".book_index.db"
        connection = connect(legacy_db)
        try:
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                + MIGRATION_001
                + "\nINSERT INTO schema_migrations(version, description) VALUES (1, 'legacy');\n"
                "PRAGMA user_version = 1;\nCOMMIT;"
            )
            with transaction(connection):
                connection.execute(
                    "INSERT INTO books(id, slug, canonical_root) VALUES (1, 'legacy', ?)",
                    (str(legacy_dir),),
                )
                document_id = connection.execute(
                    "INSERT INTO documents(book_id, kind, relative_path) VALUES (1, 'manuscript', 'texto.md')"
                ).lastrowid
                chapter_id = connection.execute(
                    """INSERT INTO chapters(document_id, ordinal, stable_key, start_line, end_line)
                       VALUES (?, 0, 'capitulo-1', 1, 2)""",
                    (document_id,),
                ).lastrowid
                content = "Cena anterior à migração."
                scene_id = connection.execute(
                    """INSERT INTO scenes(
                           chapter_id, ordinal, stable_key, start_line, end_line,
                           content, content_sha256
                       ) VALUES (?, 0, 'cena-antiga', 1, 2, ?, ?)""",
                    (chapter_id, content, hashlib.sha256(content.encode()).hexdigest()),
                ).lastrowid

            self.assertEqual(7, migrate(connection))
            upgraded = connection.execute(
                "SELECT scene_uid FROM scenes WHERE id = ?", (scene_id,)
            ).fetchone()
            self.assertEqual(32, len(upgraded["scene_uid"]))
            verify_integrity(connection)
        finally:
            connection.close()

    def test_failed_transaction_rolls_back(self) -> None:
        connection = connect(self.db_path)
        try:
            with self.assertRaises(RuntimeError):
                with transaction(connection):
                    connection.execute(
                        "INSERT INTO documents(book_id, kind, relative_path) VALUES (1, 'yaml', 'dossie.yaml')"
                    )
                    raise RuntimeError("falha simulada")
            count = connection.execute("SELECT count(*) FROM documents").fetchone()[0]
            self.assertEqual(0, count)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
