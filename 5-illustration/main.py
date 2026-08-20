#!/usr/bin/env python3
"""CLI do motor visual: diagnóstico por padrão, correção somente por confirmação."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from image_preflight import inspect_asset, prepare_asset, report_payload, save_report


def _load_plan(book_dir: Path) -> dict[str, Any]:
    path = book_dir / "plano_ilustracoes.yaml"
    if not path.exists():
        raise SystemExit(f"Plano visual não encontrado: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _support(plan: dict[str, Any], kind: str) -> tuple[tuple[int, int], tuple[float, float]]:
    key = "abertura" if kind == "abertura" else "spread"
    data = plan["composicao"][key]
    return tuple(data["tamanho_recomendado_px"]), tuple(data["tamanho_com_sangria_mm"])


def _scenes(plan: dict[str, Any], chapter: int | None):
    for item in plan.get("capitulos", plan.get("historias", [])):
        if chapter is not None and int(item.get("ordem", -1)) != chapter:
            continue
        for scene in item.get("cenas", []):
            yield scene


def _paths(book_dir: Path, scene: dict[str, Any]) -> tuple[Path, Path]:
    """Resolve o destino final e, enquanto ele não existir, a fonte aprovada."""
    destination = book_dir / scene["arquivo"]
    fallback = (scene.get("preflight") or {}).get("source_file")
    source = book_dir / fallback if not destination.exists() and fallback else destination
    return source, destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight técnico de ilustrações")
    parser.add_argument("--book-dir", required=True, help="Pasta do livro, absoluta ou relativa a inputs/")
    parser.add_argument("--chapter", type=int, help="Limita a conferência a um conto/capítulo")
    parser.add_argument("--apply", action="store_true", help="Aplica as correções indicadas; por padrão apenas avisa")
    parser.add_argument(
        "--confirm-fixes", action="store_true",
        help="Confirma que o relatório foi revisado e autoriza cópias corrigidas",
    )
    args = parser.parse_args()

    raw = Path(args.book_dir)
    book_dir = raw if raw.exists() else Path("inputs") / raw
    plan = _load_plan(book_dir)
    selected = list(_scenes(plan, args.chapter))
    if not selected:
        raise SystemExit("Nenhuma cena encontrada para o filtro informado")

    reports = []
    for scene in selected:
        path, _ = _paths(book_dir, scene)
        expected_px, expected_mm = _support(plan, scene["tipo"])
        seam = bool((scene.get("preflight") or {}).get("remove_center_seam"))
        reports.append(inspect_asset(scene["id"], path, scene["tipo"], expected_px, expected_mm, seam))

    output = Path("outputs") / book_dir.name / "illustrations" / "preflight.json"
    payload = report_payload(book_dir.name, reports)
    save_report(payload, output)
    summary = payload["summary"]
    print(f"Preflight: {payload['status']} — {summary['errors']} erro(s), {summary['warnings']} aviso(s)")
    for asset in reports:
        print(f"\n{asset.scene_id}: {asset.path}")
        for issue in asset.issues:
            marker = "corrigível" if issue.fixable else "revisão manual"
            print(f"  - {issue.severity.upper()} [{issue.code}] {issue.message} ({marker})")
    print(f"\nRelatório: {output}")

    if not args.apply:
        if any(issue.fixable for report in reports for issue in report.issues):
            print("\nNenhum arquivo foi alterado. Revise os avisos e execute novamente com --apply --confirm-fixes.")
        return
    if not args.confirm_fixes:
        raise SystemExit("Correção recusada: use --confirm-fixes somente depois de revisar o relatório acima.")
    if summary["errors"]:
        raise SystemExit("Correção recusada enquanto houver arquivos ausentes ou ilegíveis.")

    backup_root = book_dir / "assets" / "interior" / "originais" / (f"conto_{args.chapter:02d}" if args.chapter else "preflight")
    for scene, report in zip(selected, reports):
        source = Path(report.path)
        expected_px, _ = _support(plan, scene["tipo"])
        _, destination = _paths(book_dir, scene)
        seam = bool((scene.get("preflight") or {}).get("remove_center_seam"))
        prepare_asset(source, destination, backup_root, expected_px, seam)
        print(f"Preparada: {destination}")

    print(f"Originais preservados em: {backup_root}")
    print("Execute o preflight novamente sem --apply para validar os arquivos finais.")


if __name__ == "__main__":
    main()
