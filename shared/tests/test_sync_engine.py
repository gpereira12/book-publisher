from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from shared.db_engine import connect, verify_integrity
from shared.sync_engine import sync_book


INITIAL = """---
title: Romance de Teste
---

# Capítulo Um

<!-- scene:01JSCENETEST000000000000001 title=\"Encontro\" -->
Ana encontrou Bento na ponte antiga.

# Capítulo Dois

<!-- scene:01JSCENETEST000000000000002 title=\"Retorno\" -->
Bento retornou sozinho ao amanhecer.
"""


class SyncEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.temp_dir.name) / "romance"
        self.book_dir.mkdir()
        self.manuscript = self.book_dir / "texto_original.md"
        self.manuscript.write_text(INITIAL, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_first_sync_then_hash_fast_path(self) -> None:
        first = sync_book(self.book_dir, passage_target_words=10)
        second = sync_book(self.book_dir, passage_target_words=10)

        self.assertFalse(first.skipped)
        self.assertEqual(2, first.inserted_scenes)
        self.assertTrue(second.skipped)
        self.assertEqual(2, second.unchanged_scenes)

        connection = connect(first.database_path)
        try:
            self.assertEqual(2, connection.execute("SELECT count(*) FROM scenes").fetchone()[0])
            self.assertEqual(2, connection.execute("SELECT count(*) FROM passages").fetchone()[0])
            self.assertEqual(1, connection.execute("SELECT count(*) FROM sync_runs").fetchone()[0])
            recorded = connection.execute(
                """SELECT content_merkle_root, structure_merkle_root,
                          materialization_merkle_root FROM sync_runs"""
            ).fetchone()
            self.assertEqual(first.content_merkle_root, recorded["content_merkle_root"])
            self.assertEqual(first.structure_merkle_root, recorded["structure_merkle_root"])
            self.assertEqual(
                first.materialization_merkle_root,
                recorded["materialization_merkle_root"],
            )
            verify_integrity(connection)
        finally:
            connection.close()

    def test_changed_scene_preserves_uid_and_creates_patch(self) -> None:
        first = sync_book(self.book_dir, passage_target_words=10)
        connection = connect(first.database_path)
        try:
            before = connection.execute(
                "SELECT id, scene_uid FROM scenes WHERE scene_uid = '01JSCENETEST000000000000001'"
            ).fetchone()
        finally:
            connection.close()

        self.manuscript.write_text(
            INITIAL.replace(
                "Ana encontrou Bento na ponte antiga.",
                "Ana encontrou Bento e Clara na ponte antiga.",
            ),
            encoding="utf-8",
        )
        report = sync_book(self.book_dir, passage_target_words=10)
        self.assertEqual(1, report.updated_scenes)
        self.assertEqual(1, report.unchanged_scenes)
        self.assertNotEqual(first.content_merkle_root, report.content_merkle_root)
        self.assertEqual(first.structure_merkle_root, report.structure_merkle_root)
        self.assertNotEqual(
            first.materialization_merkle_root,
            report.materialization_merkle_root,
        )

        connection = connect(report.database_path)
        try:
            after = connection.execute(
                "SELECT id, scene_uid FROM scenes WHERE scene_uid = '01JSCENETEST000000000000001'"
            ).fetchone()
            self.assertEqual(before["id"], after["id"])
            self.assertEqual(before["scene_uid"], after["scene_uid"])
            revision = connection.execute(
                "SELECT patch_text FROM scene_revisions WHERE scene_id = ?", (after["id"],)
            ).fetchone()
            self.assertIn("+Ana encontrou Bento e Clara", revision["patch_text"])
            stale = connection.execute(
                """SELECT status.code
                   FROM scene_derivation_status AS materialization
                   JOIN derivation_kinds AS kind ON kind.id = materialization.derivation_kind_id
                   JOIN derivation_statuses AS status ON status.id = materialization.status_id
                   WHERE materialization.scene_id = ? AND kind.code = 'mentions'""",
                (after["id"],),
            ).fetchone()
            self.assertEqual("stale", stale[0])
            verify_integrity(connection)
        finally:
            connection.close()

    def test_removed_scene_is_deleted(self) -> None:
        first = sync_book(self.book_dir)
        shortened = INITIAL.split("# Capítulo Dois", 1)[0].rstrip() + "\n"
        self.manuscript.write_text(shortened, encoding="utf-8")
        report = sync_book(self.book_dir)

        self.assertEqual(1, report.deleted_scenes)
        connection = connect(first.database_path)
        try:
            self.assertEqual(1, connection.execute("SELECT count(*) FROM scenes").fetchone()[0])
            self.assertEqual(
                1,
                connection.execute("SELECT count(*) FROM scene_tombstones").fetchone()[0],
            )
            verify_integrity(connection)
        finally:
            connection.close()

    def test_implicit_scene_survives_chapter_rename_by_content_hash(self) -> None:
        self.manuscript.write_text("# Nome antigo\n\nCorpo imutável da cena.\n", encoding="utf-8")
        first = sync_book(self.book_dir)
        connection = connect(first.database_path)
        try:
            old_scene = connection.execute("SELECT id, scene_uid FROM scenes").fetchone()
        finally:
            connection.close()

        self.manuscript.write_text("# Nome novo\n\nCorpo imutável da cena.\n", encoding="utf-8")
        second = sync_book(self.book_dir)
        connection = connect(second.database_path)
        try:
            new_scene = connection.execute("SELECT id, scene_uid FROM scenes").fetchone()
            self.assertEqual(old_scene["id"], new_scene["id"])
            self.assertEqual(old_scene["scene_uid"], new_scene["scene_uid"])
            self.assertEqual(0, second.updated_scenes)
            self.assertEqual(1, second.unchanged_scenes)
            self.assertEqual(first.content_merkle_root, second.content_merkle_root)
            self.assertNotEqual(first.structure_merkle_root, second.structure_merkle_root)
            self.assertEqual(
                first.materialization_merkle_root,
                second.materialization_merkle_root,
            )
        finally:
            connection.close()

    def test_chunking_change_only_changes_materialization_root(self) -> None:
        first = sync_book(
            self.book_dir,
            passage_target_words=100,
            passage_overlap_paragraphs=0,
        )
        second = sync_book(
            self.book_dir,
            passage_target_words=5,
            passage_overlap_paragraphs=0,
        )
        self.assertFalse(second.skipped)
        self.assertEqual(first.content_merkle_root, second.content_merkle_root)
        self.assertEqual(first.structure_merkle_root, second.structure_merkle_root)
        self.assertNotEqual(
            first.materialization_merkle_root,
            second.materialization_merkle_root,
        )


if __name__ == "__main__":
    unittest.main()
