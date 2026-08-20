from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from shared.markdown_scene_parser import parse_markdown


class MarkdownSceneParserTests(unittest.TestCase):
    def test_explicit_markers_and_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "texto.md"
            path.write_text(
                """---
title: Teste
---

<!-- chapter:01JCHAPTEREXPLICIT000000001 title=\"Abertura\" -->
# Abertura

<!-- scene:01JSCENEEXPLICIT00000000001 title=\"Chegada\" -->
O viajante chegou à cidade.

<!-- scene:01JSCENEEXPLICIT00000000002 title=\"Portão\" -->
O portão se fechou.
""",
                encoding="utf-8",
            )
            parsed = parse_markdown(path, passage_target_words=5, passage_overlap_paragraphs=0)

        self.assertEqual(1, len(parsed.chapters))
        chapter = parsed.chapters[0]
        self.assertEqual("01JCHAPTEREXPLICIT000000001", chapter.declared_uid)
        self.assertEqual("Abertura", chapter.title)
        self.assertEqual(2, len(chapter.scenes))
        self.assertEqual("01JSCENEEXPLICIT00000000001", chapter.scenes[0].declared_uid)
        self.assertNotIn("<!--", chapter.scenes[0].content)

    def test_html_day_headings_are_chapters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "texto.md"
            path.write_text(
                """Introdução editorial.

<h3 align=\"center\">***DIA 1: Começo***</h3>

Primeiro dia.

<h3 align=\"center\">***DIA 2: Continuação***</h3>

Segundo dia.
""",
                encoding="utf-8",
            )
            parsed = parse_markdown(path)

        self.assertEqual(["Preâmbulo", "DIA 1: Começo", "DIA 2: Continuação"], [
            chapter.title for chapter in parsed.chapters
        ])

    def test_auto_detection_prefers_chapters_over_subsections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "texto.md"
            path.write_text(
                """# PARTE I

## 1. Primeiro capítulo

### Exemplo
Texto.

### Exercícios
Texto.

## 2. Segundo capítulo

### Exemplo
Texto.

### Exercícios
Texto.
""",
                encoding="utf-8",
            )
            parsed = parse_markdown(path)

        self.assertEqual(
            ["Preâmbulo", "1. Primeiro capítulo", "2. Segundo capítulo"],
            [chapter.title for chapter in parsed.chapters],
        )


if __name__ == "__main__":
    unittest.main()
