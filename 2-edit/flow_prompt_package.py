#!/usr/bin/env python3
"""Compila um pacote YAML de prompts do Google Flow em Markdown e JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


REQUIRED_PROMPT_FIELDS = {"id", "kind", "name", "aspect_ratio", "purpose", "prompt_en"}


def validate_package(package: dict[str, Any]) -> None:
    if package.get("illustration_mode") == "sem_imagens" or not package.get("generate_prompts", True):
        raise ValueError("a configuração deste livro não autoriza geração de prompts")
    if package.get("provider") != "google_flow":
        raise ValueError("provider precisa ser google_flow")
    if package.get("prompt_language") != "en":
        raise ValueError("prompt_language precisa ser en")
    prompts = package.get("reference_prompts", []) + package.get("scene_prompts", [])
    if not prompts:
        raise ValueError("o pacote não contém prompts")
    ids: list[str] = []
    for prompt in prompts:
        missing = sorted(field for field in REQUIRED_PROMPT_FIELDS if not prompt.get(field))
        if missing:
            raise ValueError(f"prompt {prompt.get('id', '?')} incompleto: {', '.join(missing)}")
        ids.append(str(prompt["id"]))
    duplicates = sorted(value for value in set(ids) if ids.count(value) > 1)
    if duplicates:
        raise ValueError(f"IDs duplicados: {', '.join(duplicates)}")


def markdown_document(package: dict[str, Any], source: Path) -> str:
    validate_package(package)
    lines = [
        f"# Google Flow — Conto {package['chapter']['order']}: {package['chapter']['title']}",
        "",
        f"> Fonte estruturada: `{source.name}`. Este pacote gera somente prompts; nenhuma arte é produzida pelo motor.",
        "",
        "## Ordem de uso",
        "",
    ]
    for index, instruction in enumerate(package.get("workflow", []), start=1):
        lines.append(f"{index}. {instruction}")
    groups = [
        ("Prompts de referência", package.get("reference_prompts", [])),
        ("Prompts das cenas", package.get("scene_prompts", [])),
    ]
    for heading, prompts in groups:
        lines.extend(["", f"## {heading}", ""])
        for item in prompts:
            lines.extend([
                f"### {item['id']} — {item['name']}",
                "",
                f"- Tipo: `{item['kind']}`",
                f"- Proporção sugerida: `{item['aspect_ratio']}`",
                f"- Objetivo: {item['purpose']}",
            ])
            if item.get("flow_name"):
                lines.append(f"- Nome a cadastrar no Flow: `{item['flow_name']}`")
            if item.get("pages"):
                lines.append(f"- Páginas: `{', '.join(map(str, item['pages']))}`")
            if item.get("layout_notes_pt"):
                lines.append(f"- Diagramação: {item['layout_notes_pt']}")
            lines.extend(["", "```text", item["prompt_en"].strip(), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def json_document(package: dict[str, Any]) -> str:
    validate_package(package)
    return json.dumps(package, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    package = yaml.safe_load(args.package.read_text(encoding="utf-8"))
    markdown_path = args.markdown or args.package.with_suffix(".md")
    json_path = args.json or args.package.with_suffix(".json")
    markdown_path.write_text(markdown_document(package, args.package), encoding="utf-8")
    json_path.write_text(json_document(package), encoding="utf-8")
    print(f"Markdown: {markdown_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
