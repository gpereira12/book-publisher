from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from book_mcp.runtime import BookMCPConfig, BookRuntime
from shared.db_engine import connect, transaction
from shared.entity_service import get_entity_dossier
from shared.search_service import search_book_context
from shared.sync_engine import sync_book


class SearchAndEntityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.temp_dir.name) / "livro"
        self.book_dir.mkdir()
        (self.book_dir / "texto_original.md").write_text(
            "# Capítulo\n\nA ametista estava escondida no jardim.\n",
            encoding="utf-8",
        )
        (self.book_dir / "texto_revisado.md").write_text(
            "# Capítulo\n\nA safira estava escondida na torre.\n",
            encoding="utf-8",
        )
        original = sync_book(self.book_dir, manuscript="texto_original.md")
        self.report = sync_book(self.book_dir, manuscript="texto_revisado.md")
        self.assertEqual(original.database_path, self.report.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_search_uses_highest_priority_active_manuscript(self) -> None:
        revised_hits = search_book_context(
            self.report.database_path, "safira torre", mode="lexical"
        )
        original_hits = search_book_context(
            self.report.database_path, "ametista jardim", mode="lexical"
        )
        self.assertEqual(1, len(revised_hits))
        self.assertEqual("texto_revisado.md", revised_hits[0].document_path)
        self.assertEqual([], original_hits)

    def test_entity_dossier_resolves_alias_and_mentions(self) -> None:
        connection = connect(self.report.database_path)
        try:
            with transaction(connection):
                entity_type = connection.execute(
                    "SELECT id FROM entity_types WHERE code = 'character'"
                ).fetchone()[0]
                entity_id = connection.execute(
                    """INSERT INTO entities(
                           book_id, entity_type_id, entity_uid,
                           canonical_name, description
                       ) VALUES (1, ?, '01JENTITYSEARCH0000000000001',
                                 'Helena', 'Guardiã da torre')""",
                    (entity_type,),
                ).lastrowid
                connection.execute(
                    "INSERT INTO entity_aliases(entity_id, alias) VALUES (?, 'A Guardiã')",
                    (entity_id,),
                )
                scene_id = connection.execute(
                    """SELECT scene.id FROM scenes AS scene
                       JOIN chapters AS chapter ON chapter.id = scene.chapter_id
                       JOIN documents AS document ON document.id = chapter.document_id
                       WHERE document.relative_path = 'texto_revisado.md'"""
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO entity_mentions(
                           entity_id, scene_id, start_offset, end_offset,
                           surface_form, confidence
                       ) VALUES (?, ?, 0, 6, 'Helena', 0.99)""",
                    (entity_id, scene_id),
                )
            dossier = get_entity_dossier(
                self.report.database_path, "A Guardiã"
            )
            self.assertEqual("Helena", dossier["canonical_name"])
            self.assertEqual(["A Guardiã"], dossier["aliases"])
            self.assertEqual(1, len(dossier["mentions"]))
        finally:
            connection.close()

    def test_book_runtime_exposes_search_scene_and_integrity(self) -> None:
        runtime = BookRuntime(
            BookMCPConfig(
                db_path=Path(self.report.database_path),
                default_search_mode="lexical",
            )
        )
        hits = runtime.search("safira", limit=2)
        self.assertEqual(1, len(hits))
        scene = runtime.scene_context(hits[0]["scene_uid"])
        self.assertIn("safira", scene["content"])
        verification = runtime.verify()
        self.assertTrue(verification["ok"])


if __name__ == "__main__":
    unittest.main()
