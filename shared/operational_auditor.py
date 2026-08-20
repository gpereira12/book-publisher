"""Auditoria read-only de invariantes entre fontes canônicas e materializações."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from shared.db_engine import connect


@dataclass(frozen=True, slots=True)
class InvariantIssue:
    code: str
    severity: str
    message: str
    owner: str | None = None


def audit_book_invariants(db_path: str | Path) -> list[InvariantIssue]:
    path = Path(db_path).expanduser().resolve()
    connection = connect(path, read_only=True)
    issues: list[InvariantIssue] = []
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            issues.append(InvariantIssue("sqlite_integrity", "critical", str(integrity)))
        for row in connection.execute("PRAGMA foreign_key_check"):
            issues.append(InvariantIssue(
                "foreign_key", "critical", f"FK inválida em {row[0]} rowid={row[1]}"
            ))
        root = Path(connection.execute("SELECT canonical_root FROM books WHERE id = 1").fetchone()[0])
        documents = connection.execute(
            """SELECT document.id, document.relative_path, document.content_sha256,
                      availability.status
               FROM documents AS document
               LEFT JOIN document_availability AS availability
                    ON availability.document_id = document.id"""
        ).fetchall()
        for document in documents:
            source = root / document["relative_path"]
            if not source.is_file():
                issues.append(InvariantIssue(
                    "source_missing", "error", "fonte canônica ausente", document["relative_path"]
                ))
                continue
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if document["content_sha256"] and digest != document["content_sha256"]:
                issues.append(InvariantIssue(
                    "source_changed", "warning", "arquivo mudou desde o último sync",
                    document["relative_path"],
                ))
            line_count = len(source.read_text(encoding="utf-8").splitlines())
            for scene in connection.execute(
                """SELECT scene.scene_uid, scene.start_line, scene.end_line,
                          scene.content, scene.content_sha256
                   FROM scenes AS scene
                   JOIN chapters AS chapter ON chapter.id = scene.chapter_id
                   WHERE chapter.document_id = ?""",
                (document["id"],),
            ):
                if scene["start_line"] < 1 or scene["end_line"] > max(line_count, 1):
                    issues.append(InvariantIssue(
                        "anchor_out_of_bounds", "error", "âncora fora do arquivo", scene["scene_uid"]
                    ))
                content_digest = hashlib.sha256(scene["content"].encode("utf-8")).hexdigest()
                if content_digest != scene["content_sha256"]:
                    issues.append(InvariantIssue(
                        "scene_hash_mismatch", "critical", "hash da cena inválido", scene["scene_uid"]
                    ))
        for row in connection.execute(
            """SELECT scene.scene_uid FROM scenes AS scene
               JOIN scene_tombstones AS tombstone ON tombstone.scene_uid = scene.scene_uid
               WHERE tombstone.restored_at IS NULL"""
        ):
            issues.append(InvariantIssue(
                "active_tombstone", "error", "cena ativa marcada como removida", row[0]
            ))
        for passage in connection.execute(
            "SELECT id, content, content_sha256 FROM passages"
        ):
            digest = hashlib.sha256(passage["content"].encode("utf-8")).hexdigest()
            if digest != passage["content_sha256"]:
                issues.append(InvariantIssue(
                    "passage_hash_mismatch", "critical", "hash da passagem inválido",
                    str(passage["id"]),
                ))
        for claim in connection.execute(
            """SELECT claim.id,
                      from_chapter.ordinal AS from_chapter,
                      valid_from.ordinal AS from_scene,
                      to_chapter.ordinal AS to_chapter,
                      valid_to.ordinal AS to_scene
               FROM entity_claims AS claim
               JOIN scenes AS valid_from ON valid_from.id = claim.valid_from_scene_id
               JOIN chapters AS from_chapter ON from_chapter.id = valid_from.chapter_id
               JOIN scenes AS valid_to ON valid_to.id = claim.valid_to_scene_id
               JOIN chapters AS to_chapter ON to_chapter.id = valid_to.chapter_id"""
        ):
            if (claim["from_chapter"], claim["from_scene"]) > (
                claim["to_chapter"], claim["to_scene"]
            ):
                issues.append(InvariantIssue(
                    "inverted_claim_interval", "error", "intervalo temporal invertido",
                    str(claim["id"]),
                ))
        for row in connection.execute(
            """SELECT document.relative_path, count(root.root_hash) AS roots
               FROM documents AS document
               LEFT JOIN document_merkle_roots AS root ON root.document_id = document.id
               GROUP BY document.id HAVING roots < 3"""
        ):
            issues.append(InvariantIssue(
                "missing_merkle_roots", "error", "documento sem os três roots", row[0]
            ))
        stale = connection.execute(
            """SELECT count(*) FROM scene_derivation_status AS derivation
               JOIN derivation_statuses AS status ON status.id = derivation.status_id
               WHERE status.code IN ('stale', 'failed')"""
        ).fetchone()[0]
        if stale:
            issues.append(InvariantIssue(
                "stale_materializations", "warning", f"{stale} materializações stale/failed"
            ))
        from shared.knowledge_governance import verify_governance_log

        try:
            verify_governance_log(root)
        except (ValueError, json.JSONDecodeError) as exc:
            issues.append(InvariantIssue(
                "governance_log_invalid", "critical", str(exc), "knowledge_reviews.jsonl"
            ))
    finally:
        connection.close()
    return issues
