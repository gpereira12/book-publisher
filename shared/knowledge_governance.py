"""Fila de propostas e decisões humanas para conhecimento não canônico."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.db_engine import connect, transaction


GOVERNANCE_LOG_FILENAME = "knowledge_reviews.jsonl"


def _book_root(db_path: str | Path) -> Path:
    connection = connect(db_path, read_only=True)
    try:
        row = connection.execute("SELECT canonical_root FROM books WHERE id = 1").fetchone()
        if row is None:
            raise RuntimeError("banco sem raiz canônica")
        return Path(row[0]).resolve()
    finally:
        connection.close()


def _canonical_event_hash(event: dict[str, Any]) -> str:
    payload = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _append_governance_event(book_root: Path, event: dict[str, Any]) -> dict[str, Any]:
    """Acrescenta evento por troca atômica e mantém uma cadeia SHA-256."""

    import fcntl

    log_path = book_root / GOVERNANCE_LOG_FILENAME
    lock_path = book_root / ".knowledge_reviews.lock"
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        previous_hash: str | None = None
        if existing.strip():
            previous_hash = json.loads(existing.splitlines()[-1])["event_hash"]
        complete = dict(
            event,
            created_at=event.get("created_at") or datetime.now(timezone.utc).isoformat(),
            previous_hash=previous_hash,
        )
        complete["event_hash"] = _canonical_event_hash(complete)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".knowledge-reviews-", suffix=".tmp", dir=book_root
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(existing)
                if existing and not existing.endswith("\n"):
                    output.write("\n")
                output.write(json.dumps(complete, ensure_ascii=False, sort_keys=True) + "\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_name, log_path)
        finally:
            temporary = Path(temporary_name)
            if temporary.exists():
                temporary.unlink()
        return complete


def verify_governance_log(book_dir: str | Path) -> int:
    path = Path(book_dir).expanduser().resolve() / GOVERNANCE_LOG_FILENAME
    if not path.exists():
        return 0
    previous_hash: str | None = None
    count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        event = json.loads(line)
        event_hash = event.pop("event_hash")
        if event.get("previous_hash") != previous_hash:
            raise ValueError(f"cadeia inválida na linha {line_number}")
        if _canonical_event_hash(event) != event_hash:
            raise ValueError(f"hash inválido na linha {line_number}")
        previous_hash = event_hash
        count += 1
    return count


def append_identity_operation_event(
    db_path: str | Path,
    event: dict[str, Any],
) -> dict[str, Any]:
    return _append_governance_event(_book_root(db_path), event)


@dataclass(frozen=True, slots=True)
class Proposal:
    proposal_uid: str
    kind: str
    status: str
    payload: dict[str, Any]


def create_knowledge_proposal(
    db_path: str | Path,
    *,
    kind: str,
    payload: dict[str, Any],
    extraction_method: str,
    source_scene_uid: str | None = None,
    source_excerpt: str | None = None,
    model_name: str | None = None,
    model_config_hash: str | None = None,
    prompt_hash: str | None = None,
    confidence: float = 1.0,
    proposal_uid: str | None = None,
) -> Proposal:
    if kind not in {"entity", "alias", "relationship", "state", "claim"}:
        raise ValueError(f"tipo de proposta inválido: {kind}")
    serialized_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(serialized_payload.encode("utf-8")) > 65_536:
        raise ValueError("payload da proposta excede 64 KiB")
    if source_excerpt and len(source_excerpt) > 4_000:
        raise ValueError("source_excerpt excede 4000 caracteres")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence deve estar entre 0 e 1")
    uid = proposal_uid or str(uuid.uuid4())
    _append_governance_event(
        _book_root(db_path),
        {
            "event_uid": uid,
            "event_type": "proposal_created",
            "proposal_uid": uid,
            "kind": kind,
            "payload": payload,
            "extraction_method": extraction_method,
            "source_scene_uid": source_scene_uid,
            "source_excerpt": source_excerpt,
            "model_name": model_name,
            "model_config_hash": model_config_hash,
            "prompt_hash": prompt_hash,
            "confidence": confidence,
        },
    )
    connection = connect(db_path)
    try:
        with transaction(connection):
            status_id = connection.execute(
                "SELECT id FROM approval_statuses WHERE code = 'suggested'"
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO knowledge_proposals(
                       proposal_uid, proposal_kind, payload_json,
                       source_scene_uid, source_excerpt, extraction_method,
                       model_name, model_config_hash, prompt_hash, confidence,
                       status_id
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(proposal_uid) DO NOTHING""",
                (
                    uid, kind, serialized_payload,
                    source_scene_uid, source_excerpt, extraction_method, model_name,
                    model_config_hash, prompt_hash, confidence, status_id,
                ),
            )
    finally:
        connection.close()
    return Proposal(uid, kind, "suggested", payload)


def decide_knowledge_proposal(
    db_path: str | Path,
    proposal_uid: str,
    *,
    decision: str,
    reviewer: str,
    rationale: str | None = None,
) -> Proposal:
    if decision not in {"approved", "rejected", "superseded"}:
        raise ValueError("decision deve ser approved, rejected ou superseded")
    allowed = {
        "suggested": {"approved", "rejected"},
        "approved": {"superseded"},
        "rejected": set(),
        "superseded": set(),
    }
    connection = connect(db_path)
    try:
        proposal = connection.execute(
                """SELECT proposal.*, status.code AS status
                   FROM knowledge_proposals AS proposal
                   JOIN approval_statuses AS status ON status.id = proposal.status_id
                   WHERE proposal.proposal_uid = ?""",
                (proposal_uid,),
            ).fetchone()
        if proposal is None:
            raise KeyError(f"proposta não encontrada: {proposal_uid}")
        if decision not in allowed[proposal["status"]]:
            raise ValueError(
                f"transição inválida: {proposal['status']} -> {decision}"
            )
        decision_uid = str(uuid.uuid4())
        _append_governance_event(
            _book_root(db_path),
            {
                "event_uid": decision_uid,
                "event_type": "proposal_decided",
                "decision_uid": decision_uid,
                "proposal_uid": proposal_uid,
                "from_status": proposal["status"],
                "to_status": decision,
                "reviewer": reviewer,
                "rationale": rationale,
            },
        )
        with transaction(connection):
            target = connection.execute(
                "SELECT id FROM approval_statuses WHERE code = ?", (decision,)
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO knowledge_approval_decisions(
                       decision_uid, proposal_id, from_status_id, to_status_id,
                       reviewer, rationale
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    decision_uid, proposal["id"], proposal["status_id"],
                    target, reviewer, rationale,
                ),
            )
            connection.execute(
                """UPDATE knowledge_proposals SET status_id = ?,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (target, proposal["id"]),
            )
            from shared.merkle import refresh_current_work_knowledge_root

            refresh_current_work_knowledge_root(connection)
            payload = json.loads(proposal["payload_json"])
            return Proposal(proposal_uid, proposal["proposal_kind"], decision, payload)
    finally:
        connection.close()


def list_knowledge_proposals(
    db_path: str | Path,
    *,
    status: str = "suggested",
    limit: int = 100,
) -> list[Proposal]:
    connection = connect(db_path, read_only=True)
    try:
        return [
            Proposal(row["proposal_uid"], row["proposal_kind"], row["status"], json.loads(row["payload_json"]))
            for row in connection.execute(
                """SELECT proposal.proposal_uid, proposal.proposal_kind,
                          proposal.payload_json, status.code AS status
                   FROM knowledge_proposals AS proposal
                   JOIN approval_statuses AS status ON status.id = proposal.status_id
                   WHERE status.code = ? ORDER BY proposal.id LIMIT ?""",
                (status, limit),
            )
        ]
    finally:
        connection.close()


def replay_governance_log(
    book_dir: str | Path,
    *,
    db_path: str | Path | None = None,
) -> int:
    """Reconstrói a projeção SQLite a partir do log canônico validado."""

    from shared.db_engine import database_path

    root = Path(book_dir).expanduser().resolve()
    count = verify_governance_log(root)
    log_path = root / GOVERNANCE_LOG_FILENAME
    if not log_path.exists():
        return 0
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    connection = connect(db_path or database_path(root))
    try:
        with transaction(connection):
            connection.execute("DELETE FROM knowledge_approval_decisions")
            connection.execute("DELETE FROM knowledge_proposals")
            statuses = {
                row["code"]: row["id"]
                for row in connection.execute("SELECT id, code FROM approval_statuses")
            }
            for event in events:
                if event["event_type"] == "proposal_created":
                    connection.execute(
                        """INSERT INTO knowledge_proposals(
                               proposal_uid, proposal_kind, payload_json,
                               source_scene_uid, source_excerpt, extraction_method,
                               model_name, model_config_hash, prompt_hash, confidence,
                               status_id, created_at, updated_at
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            event["proposal_uid"], event["kind"],
                            json.dumps(event["payload"], ensure_ascii=False, sort_keys=True),
                            event.get("source_scene_uid"), event.get("source_excerpt"),
                            event["extraction_method"], event.get("model_name"),
                            event.get("model_config_hash"), event.get("prompt_hash"),
                            event.get("confidence", 1.0), statuses["suggested"],
                            event["created_at"], event["created_at"],
                        ),
                    )
                elif event["event_type"] == "proposal_decided":
                    proposal = connection.execute(
                        "SELECT id, status_id FROM knowledge_proposals WHERE proposal_uid = ?",
                        (event["proposal_uid"],),
                    ).fetchone()
                    if proposal is None:
                        raise ValueError(
                            f"decisão antes da proposta: {event['proposal_uid']}"
                        )
                    from_status = statuses[event["from_status"]]
                    if proposal["status_id"] != from_status:
                        raise ValueError(
                            f"estado divergente para proposta {event['proposal_uid']}"
                        )
                    to_status = statuses[event["to_status"]]
                    connection.execute(
                        """INSERT INTO knowledge_approval_decisions(
                               decision_uid, proposal_id, from_status_id, to_status_id,
                               reviewer, rationale, decided_at
                           ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            event["decision_uid"], proposal["id"], from_status,
                            to_status, event["reviewer"], event.get("rationale"),
                            event["created_at"],
                        ),
                    )
                    connection.execute(
                        "UPDATE knowledge_proposals SET status_id = ?, updated_at = ? WHERE id = ?",
                        (to_status, event["created_at"], proposal["id"]),
                    )
            from shared.merkle import refresh_current_work_knowledge_root

            refresh_current_work_knowledge_root(connection)
    finally:
        connection.close()
    from shared.entity_identity import merge_entities, split_entity

    for event in events:
        if event["event_type"] == "entity_merged":
            merge_entities(
                db_path or database_path(root),
                source_uid=event["source_uid"],
                target_uid=event["target_uid"],
                actor=event["actor"],
                reason=event.get("reason"),
                event_uid=event["event_uid"],
                _record_canonical=False,
            )
        elif event["event_type"] == "entity_split":
            split_entity(
                db_path or database_path(root),
                source_uid=event["source_uid"],
                new_name=event["new_name"],
                actor=event["actor"],
                alias_names=event.get("alias_names"),
                new_uid=event["new_uid"],
                reason=event.get("reason"),
                event_uid=event["event_uid"],
                _record_canonical=False,
            )
    return count
