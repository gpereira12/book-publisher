import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import resolve_source_file, write_active_revision, write_versioned_revision
from review_models import make_finding, stable_finding_id


class ReviewModelsTests(unittest.TestCase):
    def test_finding_has_stable_id_and_location(self):
        text = "# Conto\n\nPrimeiro parágrafo.\n\nUma expressão importante aparece aqui."
        finding = make_finding(
            text=text,
            rule="test.rule",
            category="estilo",
            severity="observacao",
            confidence=0.8,
            excerpt="expressão importante",
            explanation="Teste",
        )
        self.assertEqual(finding.line, 5)
        self.assertEqual(finding.chapter, "Conto")
        self.assertEqual(finding.id, stable_finding_id("test.rule", 5, "expressão importante"))

    def test_invalid_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            make_finding(
                text="texto",
                rule="test.rule",
                category="teste",
                severity="urgente",
                confidence=0.5,
                excerpt="texto",
                explanation="Teste",
            )


class SafeRevisionTests(unittest.TestCase):
    def test_auto_source_prefers_existing_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            (book_dir / "texto_original.md").write_text("original", encoding="utf-8")
            revised = book_dir / "texto_revisado.md"
            revised.write_text("revisado", encoding="utf-8")
            self.assertEqual(resolve_source_file(book_dir, "auto"), revised)

    def test_active_revision_is_backed_up_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            target = book_dir / "texto_revisado.md"
            target.write_text("versão humana", encoding="utf-8")
            written, backup = write_active_revision(book_dir, "versão normalizada")
            self.assertEqual(written.read_text(encoding="utf-8"), "versão normalizada")
            self.assertIsNotNone(backup)
            self.assertEqual(backup.read_text(encoding="utf-8"), "versão humana")

    def test_versioned_revision_does_not_change_active_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            active = book_dir / "texto_revisado.md"
            active.write_text("versão ativa", encoding="utf-8")
            created = write_versioned_revision(
                book_dir,
                "nova versão",
                now=datetime(2026, 8, 9, tzinfo=timezone.utc),
            )
            self.assertEqual(active.read_text(encoding="utf-8"), "versão ativa")
            self.assertEqual(created.read_text(encoding="utf-8"), "nova versão")
            self.assertIn("20260809", created.name)


if __name__ == "__main__":
    unittest.main()
