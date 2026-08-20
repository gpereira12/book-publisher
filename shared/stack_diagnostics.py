"""Diagnóstico sem download do stack local FTS5/sqlite-vec/FastEmbed/MCP."""

from __future__ import annotations

import argparse
import importlib
import json
import sqlite3
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ComponentDiagnostic:
    component: str
    available: bool
    version: str | None
    detail: str


def diagnose_optional_stack() -> list[ComponentDiagnostic]:
    diagnostics: list[ComponentDiagnostic] = []
    connection = sqlite3.connect(":memory:")
    try:
        try:
            connection.execute("CREATE VIRTUAL TABLE probe_fts USING fts5(content)")
        except sqlite3.Error as exc:
            diagnostics.append(ComponentDiagnostic("fts5", False, sqlite3.sqlite_version, str(exc)))
        else:
            diagnostics.append(ComponentDiagnostic("fts5", True, sqlite3.sqlite_version, "virtual table criada"))
    finally:
        connection.close()

    for module_name, label in (("sqlite_vec", "sqlite-vec"), ("fastembed", "FastEmbed"), ("mcp", "MCP SDK")):
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            diagnostics.append(ComponentDiagnostic(label, False, None, str(exc)))
            continue
        version = getattr(module, "__version__", None)
        detail = "importado"
        if module_name == "sqlite_vec":
            probe = sqlite3.connect(":memory:")
            try:
                module.load(probe)
                probe.execute("CREATE VIRTUAL TABLE probe_vec USING vec0(embedding FLOAT[4])")
                detail = "extensão carregada e vec0 criado"
            except Exception as exc:  # diagnóstico, não falha da aplicação
                diagnostics.append(ComponentDiagnostic(label, False, version, str(exc)))
                continue
            finally:
                probe.close()
        diagnostics.append(ComponentDiagnostic(label, True, version, detail))
    return diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnostica dependências locais sem download")
    parser.parse_args()
    print(json.dumps([asdict(item) for item in diagnose_optional_stack()], indent=2))


if __name__ == "__main__":
    main()

