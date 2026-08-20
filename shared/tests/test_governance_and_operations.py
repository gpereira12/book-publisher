from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from shared.db_engine import connect
from shared.entity_identity import merge_entities, split_entity
from shared.entity_service import get_entity_dossier
from shared.knowledge_contract import KnowledgeContractError, validate_knowledge_payload
from shared.knowledge_governance import (
    create_knowledge_proposal,
    decide_knowledge_proposal,
    list_knowledge_proposals,
)
from shared.knowledge_sync import sync_knowledge_yaml
from shared.operational_auditor import audit_book_invariants
from shared.reliability import (
    rebuild_book_index,
    restore_book_index,
    verify_database_backup,
    writer_lease,
)
from shared.stack_diagnostics import diagnose_optional_stack
from shared.sync_engine import sync_book


MANUSCRIPT = """# Capítulo

<!-- scene:01JGOVERNANCETEST000000001 -->
Ana e Anne encontraram Bento.
"""


class GovernanceAndOperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.book = Path(self.temp.name) / "book"
        self.book.mkdir()
        (self.book / "texto_original.md").write_text(MANUSCRIPT, encoding="utf-8")
        self.report = sync_book(self.book)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_knowledge(self, text: str) -> Path:
        path = self.book / "knowledge.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_contract_and_typed_predicate(self) -> None:
        with self.assertRaises(KnowledgeContractError):
            validate_knowledge_payload({"schema_version": 99, "entities": []})
        self._write_knowledge(
            """schema_version: 1
entities:
  - name: Ana
    type: character
predicates:
  - code: idade
    value_kind: number
    cardinality: single
    temporal_mode: point
claims:
  - subject: Ana
    predicate: idade
    value: antiga
    scene_uid: 01JGOVERNANCETEST000000001
"""
        )
        with self.assertRaisesRegex(ValueError, "esperado number"):
            sync_knowledge_yaml(self.book)
        self._write_knowledge(
            (self.book / "knowledge.yaml").read_text(encoding="utf-8").replace(
                "value: antiga", "value: 37"
            )
        )
        result = sync_knowledge_yaml(self.book)
        self.assertEqual(1, result.claims)

    def test_proposal_requires_human_decision(self) -> None:
        proposal = create_knowledge_proposal(
            self.report.database_path,
            kind="claim",
            payload={"subject": "Ana", "predicate": "status", "value": "viva"},
            extraction_method="test-model",
            source_scene_uid="01JGOVERNANCETEST000000001",
            model_name="fake-local",
            confidence=0.8,
        )
        self.assertEqual("suggested", proposal.status)
        self.assertEqual(1, len(list_knowledge_proposals(self.report.database_path)))
        approved = decide_knowledge_proposal(
            self.report.database_path,
            proposal.proposal_uid,
            decision="approved",
            reviewer="editor@test",
            rationale="Confirmado no manuscrito",
        )
        self.assertEqual("approved", approved.status)
        rebuild_book_index(self.book)
        self.assertEqual(
            1,
            len(list_knowledge_proposals(self.report.database_path, status="approved")),
        )
        connection = connect(self.report.database_path)
        try:
            self.assertEqual(0, connection.execute("SELECT count(*) FROM entity_claims").fetchone()[0])
            self.assertEqual(1, connection.execute("SELECT count(*) FROM knowledge_approval_decisions").fetchone()[0])
        finally:
            connection.close()

    def test_merge_redirect_and_split_are_auditable(self) -> None:
        self._write_knowledge(
            """schema_version: 1
entities:
  - uid: 01JENTITYANA000000000000001
    name: Ana
    type: character
  - uid: 01JENTITYANNE00000000000001
    name: Anne
    type: character
    aliases: [Aninha]
"""
        )
        sync_knowledge_yaml(self.book)
        result_uid = merge_entities(
            self.report.database_path,
            source_uid="01JENTITYANNE00000000000001",
            target_uid="01JENTITYANA000000000000001",
            actor="editor@test",
            reason="Duplicata",
        )
        self.assertEqual("01JENTITYANA000000000000001", result_uid)
        dossier = get_entity_dossier(
            self.report.database_path, "01JENTITYANNE00000000000001"
        )
        self.assertEqual(result_uid, dossier["entity_uid"])
        split_uid = split_entity(
            self.report.database_path,
            source_uid=result_uid,
            new_name="Ana da Outra Continuidade",
            alias_names=["Aninha"],
            actor="editor@test",
        )
        split_dossier = get_entity_dossier(self.report.database_path, split_uid)
        self.assertIn("Aninha", split_dossier["aliases"])
        rebuild_book_index(self.book)
        redirected_after_rebuild = get_entity_dossier(
            self.report.database_path, "01JENTITYANNE00000000000001"
        )
        self.assertEqual(result_uid, redirected_after_rebuild["entity_uid"])
        self.assertEqual(
            split_uid,
            get_entity_dossier(self.report.database_path, split_uid)["entity_uid"],
        )
        connection = connect(self.report.database_path)
        try:
            self.assertEqual(2, connection.execute("SELECT count(*) FROM entity_identity_operations").fetchone()[0])
        finally:
            connection.close()

    def test_lease_renews_and_backup_restores(self) -> None:
        db_path = Path(self.report.database_path)
        with writer_lease(db_path, lease_name="long-test", ttl_seconds=5):
            connection = connect(db_path)
            try:
                before = connection.execute(
                    "SELECT expires_at_epoch FROM writer_leases WHERE lease_name = 'long-test'"
                ).fetchone()[0]
            finally:
                connection.close()
            time.sleep(2.0)
            connection = connect(db_path)
            try:
                after = connection.execute(
                    "SELECT expires_at_epoch FROM writer_leases WHERE lease_name = 'long-test'"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertGreater(after, before)

        rebuild_book_index(self.book)
        backup = sorted(self.book.glob(".book_index.db.backup-*"))[-1]
        self.assertEqual("ok", verify_database_backup(backup).integrity)
        connection = connect(db_path)
        try:
            connection.execute("DELETE FROM scenes")
            self.assertEqual(0, connection.execute("SELECT count(*) FROM scenes").fetchone()[0])
        finally:
            connection.close()
        restore_book_index(self.book, backup_path=backup)
        connection = connect(db_path)
        try:
            self.assertEqual(1, connection.execute("SELECT count(*) FROM scenes").fetchone()[0])
        finally:
            connection.close()

    def test_operational_audit_and_stack_diagnostic(self) -> None:
        issues = audit_book_invariants(self.report.database_path)
        self.assertFalse([issue for issue in issues if issue.severity in {"error", "critical"}])
        diagnostics = diagnose_optional_stack()
        fts = next(item for item in diagnostics if item.component == "fts5")
        self.assertTrue(fts.available)


if __name__ == "__main__":
    unittest.main()
