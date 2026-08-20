from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shared.continuity_auditor import audit_book_continuity
from shared.db_engine import connect
from shared.knowledge_sync import sync_knowledge_yaml
from shared.reliability import rebuild_book_index, reconcile_documents
from shared.sync_engine import sync_book
from shared.universe_sync import sync_universe


MANUSCRIPT = """# Capítulo Um

<!-- scene:01JKNOWLEDGETEST0000000001 title="Encontro" -->
Ana encontrou Bento na ponte.

# Capítulo Dois

<!-- scene:01JKNOWLEDGETEST0000000002 title="Retorno" -->
Bento retornou sozinho.
"""


class ReliabilityAndKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.book = self.root / "book"
        self.book.mkdir()
        self.manuscript = self.book / "texto_original.md"
        self.manuscript.write_text(MANUSCRIPT, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_tombstone_archives_revision_history(self) -> None:
        report = sync_book(self.book)
        self.manuscript.write_text(
            MANUSCRIPT.replace("Ana encontrou Bento", "Ana reencontrou Bento"),
            encoding="utf-8",
        )
        sync_book(self.book)
        self.manuscript.write_text("# Único\n\nOutra cena permanece.\n", encoding="utf-8")
        sync_book(self.book)
        connection = connect(report.database_path)
        try:
            self.assertGreaterEqual(
                connection.execute("SELECT count(*) FROM scene_tombstones").fetchone()[0], 2
            )
            self.assertEqual(
                1,
                connection.execute("SELECT count(*) FROM archived_scene_revisions").fetchone()[0],
            )
            self.assertEqual(0, len(connection.execute("PRAGMA foreign_key_check").fetchall()))
        finally:
            connection.close()

    def test_failed_attempt_survives_main_failure(self) -> None:
        first = sync_book(self.book)
        with patch("shared.sync_engine._sync_book_unlocked", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                sync_book(self.book)
        connection = connect(first.database_path)
        try:
            row = connection.execute(
                "SELECT status, error_type, error_message FROM sync_attempts ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertEqual("failed", row["status"])
            self.assertEqual("RuntimeError", row["error_type"])
            self.assertIn("boom", row["error_message"])
            self.assertEqual(0, connection.execute("SELECT count(*) FROM writer_leases").fetchone()[0])
        finally:
            connection.close()

    def test_reconcile_and_atomic_rebuild(self) -> None:
        first = sync_book(self.book)
        self.manuscript.rename(self.book / "fonte_temporariamente_ausente.md")
        reconciled = reconcile_documents(self.book)
        self.assertEqual(1, reconciled.missing)
        (self.book / "fonte_temporariamente_ausente.md").rename(self.manuscript)
        reconcile_documents(self.book)
        rebuilt = rebuild_book_index(self.book)
        self.assertEqual(Path(first.database_path), rebuilt)
        self.assertTrue(list(self.book.glob(".book_index.db.backup-*")))
        connection = connect(rebuilt)
        try:
            self.assertEqual(2, connection.execute("SELECT count(*) FROM scenes").fetchone()[0])
        finally:
            connection.close()

    def test_yaml_entities_mentions_claims_and_authority_audit(self) -> None:
        report = sync_book(self.book)
        knowledge = self.book / "knowledge.yaml"
        knowledge.write_text(
            """entities:
  - name: Ana
    type: character
    aliases: [Aninha]
  - name: Bento
    type: character
claims:
  - subject: Ana
    predicate: status
    value: viva
    scene_uid: 01JKNOWLEDGETEST0000000001
relationships:
  - source: Ana
    target: Bento
    type: conhece
""",
            encoding="utf-8",
        )
        result = sync_knowledge_yaml(self.book)
        self.assertEqual(2, result.entities)
        self.assertEqual(3, result.mentions)
        self.assertEqual(1, result.claims)
        # Reingestão substitui claims pertencentes à mesma fonte, sem duplicá-los.
        sync_knowledge_yaml(self.book)
        rebuild_book_index(self.book)
        connection = connect(report.database_path)
        try:
            self.assertEqual(1, connection.execute("SELECT count(*) FROM entity_claims").fetchone()[0])
            base = connection.execute("SELECT * FROM entity_claims LIMIT 1").fetchone()
            connection.execute(
                """INSERT INTO entity_claims(
                       subject_entity_id, predicate_id, object_value_json,
                       asserted_scene_id, extraction_method, authority_source_id
                   ) VALUES (?, ?, '"morta"', ?, 'manual', ?)""",
                (
                    base["subject_entity_id"], base["predicate_id"], base["asserted_scene_id"],
                    base["authority_source_id"],
                ),
            )
        finally:
            connection.close()
        issues = audit_book_continuity(report.database_path)
        self.assertEqual("error", issues[0].severity)

    def test_universe_sync_maps_shared_entities(self) -> None:
        sync_book(self.book)
        knowledge = self.book / "knowledge.yaml"
        knowledge.write_text(
            """entities:
  - name: Ana
    type: character
    universe_uid: urn:universe:test:ana
  - name: Bento
    type: character
    universe_uid: urn:universe:test:bento
relationships:
  - source: Ana
    target: Bento
    type: conhece
    from_scene_uid: 01JKNOWLEDGETEST0000000001
claims:
  - subject: Ana
    predicate: status
    value: viva
    scene_uid: 01JKNOWLEDGETEST0000000001
""",
            encoding="utf-8",
        )
        sync_knowledge_yaml(self.book)
        universe = self.root / "universe"
        universe.mkdir()
        result = sync_universe(
            universe,
            universe_uid="urn:universe:test",
            book_dirs=[self.book],
        )
        self.assertEqual(1, result.works)
        self.assertEqual(2, result.mappings)
        self.assertEqual(1, result.relationships)
        self.assertEqual(1, result.claims)


if __name__ == "__main__":
    unittest.main()
