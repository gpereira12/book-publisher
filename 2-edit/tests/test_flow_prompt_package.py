import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flow_prompt_package import json_document, markdown_document, validate_package


def package():
    prompt = {
        "id": "scene_1", "kind": "scene", "name": "Scene", "aspect_ratio": "3:4",
        "purpose": "Test", "prompt_en": "Create an illustration without text.",
    }
    return {
        "provider": "google_flow", "prompt_language": "en",
        "illustration_mode": "totalmente_ilustrado", "generate_prompts": True,
        "chapter": {"order": 1, "title": "Story"}, "workflow": ["Create reference."],
        "reference_prompts": [], "scene_prompts": [prompt],
    }


class FlowPromptPackageTests(unittest.TestCase):
    def test_valid_package_compiles_to_markdown_and_json(self):
        data = package()
        markdown = markdown_document(data, Path("story.yaml"))
        self.assertIn("Google Flow", markdown)
        self.assertIn("```text", markdown)
        self.assertIn('"provider": "google_flow"', json_document(data))

    def test_rejects_non_english_operational_prompts(self):
        data = package()
        data["prompt_language"] = "pt-BR"
        with self.assertRaises(ValueError):
            validate_package(data)

    def test_rejects_duplicate_prompt_ids(self):
        data = package()
        data["reference_prompts"] = [dict(data["scene_prompts"][0])]
        with self.assertRaises(ValueError):
            validate_package(data)

    def test_rejects_prompt_work_for_book_without_images(self):
        data = package()
        data["illustration_mode"] = "sem_imagens"
        with self.assertRaises(ValueError):
            validate_package(data)


if __name__ == "__main__":
    unittest.main()
