from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from shared.db_engine import connect, transaction, verify_integrity
from shared.sync_engine import sync_book
from shared.universe_db_engine import (
    LATEST_UNIVERSE_SCHEMA_VERSION,
    import_book_merkle_roots,
    initialize_universe_database,
    refresh_universe_merkle_roots,
)


class UniverseDatabaseEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.universe_dir = Path(self.temp_dir.name) / "universes" / "legendarium"
        self.universe_dir.mkdir(parents=True)
        self.db_path = initialize_universe_database(
            self.universe_dir,
            universe_uid="urn:universe:legendarium",
            slug="legendarium",
            name="Legendarium",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initialization_is_idempotent(self) -> None:
        initialize_universe_database(
            self.universe_dir,
            universe_uid="urn:universe:legendarium",
            slug="legendarium",
            name="Legendarium revisado",
        )
        connection = connect(self.db_path)
        try:
            self.assertEqual(
                LATEST_UNIVERSE_SCHEMA_VERSION,
                connection.execute("PRAGMA user_version").fetchone()[0],
            )
            self.assertEqual(
                "Legendarium revisado",
                connection.execute("SELECT name FROM universes WHERE id = 1").fetchone()[0],
            )
            verify_integrity(connection)
        finally:
            connection.close()

    def test_maps_local_entities_without_cross_database_foreign_keys(self) -> None:
        connection = connect(self.db_path)
        try:
            with transaction(connection):
                work_a = connection.execute(
                    "INSERT INTO works(work_uid, title, book_db_relative_path) VALUES (?, ?, ?)",
                    ("urn:book:a", "Livro A", "../../livro_a/.book_index.db"),
                ).lastrowid
                work_b = connection.execute(
                    "INSERT INTO works(work_uid, title, book_db_relative_path) VALUES (?, ?, ?)",
                    ("urn:book:b", "Livro B", "../../livro_b/.book_index.db"),
                ).lastrowid
                character_type = connection.execute(
                    "SELECT id FROM entity_types WHERE code = 'character'"
                ).fetchone()[0]
                entity_id = connection.execute(
                    """INSERT INTO universe_entities(entity_uid, entity_type_id, canonical_name)
                       VALUES ('urn:entity:the-wanderer', ?, 'O Peregrino')""",
                    (character_type,),
                ).lastrowid
                same_identity = connection.execute(
                    "SELECT id FROM mapping_kinds WHERE code = 'same_identity'"
                ).fetchone()[0]
                connection.executemany(
                    """INSERT INTO work_entity_mappings(
                           universe_entity_id, work_id, local_entity_uid,
                           mapping_kind_id, confidence
                       ) VALUES (?, ?, ?, ?, ?)""",
                    [
                        (entity_id, work_a, "01JLOCALENTITY0000000000001", same_identity, 1.0),
                        (entity_id, work_b, "01JLOCALENTITY0000000000002", same_identity, 0.98),
                    ],
                )

            mappings = connection.execute(
                """SELECT w.title, m.local_entity_uid
                   FROM work_entity_mappings AS m
                   JOIN works AS w ON w.id = m.work_id
                   WHERE m.universe_entity_id = ?
                   ORDER BY w.title""",
                (entity_id,),
            ).fetchall()
            self.assertEqual(["Livro A", "Livro B"], [row["title"] for row in mappings])
            with transaction(connection):
                roots = refresh_universe_merkle_roots(connection)
            self.assertEqual(64, len(roots.knowledge or ""))
            verify_integrity(connection)
        finally:
            connection.close()

    def test_imports_book_roots_and_builds_universe_roots(self) -> None:
        book_dir = Path(self.temp_dir.name) / "book_a"
        book_dir.mkdir()
        (book_dir / "texto_original.md").write_text(
            "# Capítulo\n\nTexto da obra conectada.\n", encoding="utf-8"
        )
        book_report = sync_book(book_dir)
        work_uid = "urn:book:book_a"
        book_connection = connect(book_report.database_path, read_only=True)
        try:
            local_work_roots = {
                row["code"]: row["root_hash"]
                for row in book_connection.execute(
                    """SELECT kind.code, root.root_hash
                       FROM work_merkle_roots AS root
                       JOIN merkle_root_kinds AS kind ON kind.id = root.root_kind_id"""
                )
            }
        finally:
            book_connection.close()

        connection = connect(self.db_path)
        try:
            with transaction(connection):
                connection.execute(
                    """INSERT INTO works(work_uid, title, book_db_relative_path)
                       VALUES (?, 'Livro A', ?)""",
                    (work_uid, str(Path(book_report.database_path))),
                )
                imported = import_book_merkle_roots(
                    connection,
                    work_uid=work_uid,
                    book_db_path=book_report.database_path,
                )
                universe = refresh_universe_merkle_roots(connection)

            self.assertEqual(local_work_roots["content"], imported.content)
            self.assertEqual(local_work_roots["structure"], imported.structure)
            self.assertEqual(64, len(universe.content))
            self.assertEqual(64, len(universe.knowledge or ""))
            self.assertEqual(
                4,
                connection.execute(
                    "SELECT count(*) FROM universe_merkle_roots"
                ).fetchone()[0],
            )
            verify_integrity(connection)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
