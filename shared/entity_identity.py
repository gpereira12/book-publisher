"""Operações auditáveis de resolução, merge e split de entidades."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from shared.db_engine import connect, transaction


def resolve_entity_uid(connection: sqlite3.Connection, entity_uid: str) -> sqlite3.Row | None:
    row = connection.execute("SELECT * FROM entities WHERE entity_uid = ?", (entity_uid,)).fetchone()
    if row is not None:
        return row
    return connection.execute(
        """SELECT entity.* FROM entity_redirects AS redirect
           JOIN entities AS entity ON entity.id = redirect.target_entity_id
           WHERE redirect.source_entity_uid = ?""",
        (entity_uid,),
    ).fetchone()


def merge_entities(
    db_path: str | Path,
    *,
    source_uid: str,
    target_uid: str,
    actor: str,
    reason: str | None = None,
    event_uid: str | None = None,
    _record_canonical: bool = True,
) -> str:
    if source_uid == target_uid:
        raise ValueError("source_uid e target_uid devem ser diferentes")
    validation_connection = connect(db_path, read_only=True)
    try:
        validation_source = resolve_entity_uid(validation_connection, source_uid)
        validation_target = resolve_entity_uid(validation_connection, target_uid)
        if validation_source is None or validation_target is None:
            raise KeyError("entidade source ou target não encontrada")
        if validation_source["id"] == validation_target["id"]:
            return validation_target["entity_uid"]
    finally:
        validation_connection.close()
    operation_uid = event_uid or str(uuid.uuid4())
    if event_uid:
        idempotency_connection = connect(db_path, read_only=True)
        try:
            previous = idempotency_connection.execute(
                "SELECT result_uids_json FROM entity_identity_operations WHERE event_uid = ?",
                (operation_uid,),
            ).fetchone()
            if previous:
                return json.loads(previous[0])[0]
        finally:
            idempotency_connection.close()
    if _record_canonical:
        from shared.knowledge_governance import append_identity_operation_event

        append_identity_operation_event(
            db_path,
            {
                "event_uid": operation_uid,
                "event_type": "entity_merged",
                "source_uid": source_uid,
                "target_uid": target_uid,
                "actor": actor,
                "reason": reason,
            },
        )
    connection = connect(db_path)
    try:
        with transaction(connection):
            previous = connection.execute(
                "SELECT result_uids_json FROM entity_identity_operations WHERE event_uid = ?",
                (operation_uid,),
            ).fetchone()
            if previous:
                return json.loads(previous[0])[0]
            source = resolve_entity_uid(connection, source_uid)
            target = resolve_entity_uid(connection, target_uid)
            if source is None or target is None:
                raise KeyError("entidade source ou target não encontrada")
            if source["id"] == target["id"]:
                return target["entity_uid"]

            connection.execute(
                """INSERT OR IGNORE INTO entity_aliases(
                       entity_id, alias, extraction_method, source_relative_path
                   ) SELECT ?, alias, extraction_method, source_relative_path
                     FROM entity_aliases WHERE entity_id = ?""",
                (target["id"], source["id"]),
            )
            connection.execute(
                "INSERT OR IGNORE INTO entity_aliases(entity_id, alias) VALUES (?, ?)",
                (target["id"], source["canonical_name"]),
            )
            connection.execute(
                """INSERT OR IGNORE INTO entity_mentions(
                       entity_id, scene_id, start_offset, end_offset, surface_form,
                       confidence, extraction_method, source_relative_path
                   ) SELECT ?, scene_id, start_offset, end_offset, surface_form,
                            confidence, extraction_method, source_relative_path
                     FROM entity_mentions WHERE entity_id = ?""",
                (target["id"], source["id"]),
            )
            for relation in connection.execute(
                """SELECT * FROM entity_relationships
                   WHERE source_entity_id = ? OR target_entity_id = ?""",
                (source["id"], source["id"]),
            ).fetchall():
                new_source = target["id"] if relation["source_entity_id"] == source["id"] else relation["source_entity_id"]
                new_target = target["id"] if relation["target_entity_id"] == source["id"] else relation["target_entity_id"]
                if new_source == new_target:
                    continue
                exists = connection.execute(
                    """SELECT 1 FROM entity_relationships
                       WHERE source_entity_id = ? AND target_entity_id = ?
                         AND relationship_type_id = ? AND valid_from_scene_id IS ?""",
                    (new_source, new_target, relation["relationship_type_id"], relation["valid_from_scene_id"]),
                ).fetchone()
                if not exists:
                    connection.execute(
                        """INSERT INTO entity_relationships(
                               source_entity_id, target_entity_id, relationship_type_id,
                               valid_from_scene_id, valid_to_scene_id, notes,
                               extraction_method, source_relative_path
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            new_source, new_target, relation["relationship_type_id"],
                            relation["valid_from_scene_id"], relation["valid_to_scene_id"],
                            relation["notes"], relation["extraction_method"],
                            relation["source_relative_path"],
                        ),
                    )
            connection.execute(
                "UPDATE entity_claims SET subject_entity_id = ? WHERE subject_entity_id = ?",
                (target["id"], source["id"]),
            )
            connection.execute(
                "UPDATE entity_claims SET object_entity_id = ? WHERE object_entity_id = ?",
                (target["id"], source["id"]),
            )
            # Eventos conflitantes permanecem separados por ordinal novo.
            for event in connection.execute(
                "SELECT * FROM entity_state_events WHERE entity_id = ? ORDER BY id",
                (source["id"],),
            ).fetchall():
                ordinal = event["event_ordinal"]
                while connection.execute(
                    "SELECT 1 FROM entity_state_events WHERE entity_id = ? AND scene_id = ? AND event_ordinal = ?",
                    (target["id"], event["scene_id"], ordinal),
                ).fetchone():
                    ordinal += 1
                connection.execute(
                    "UPDATE entity_state_events SET entity_id = ?, event_ordinal = ? WHERE id = ?",
                    (target["id"], ordinal, event["id"]),
                )
            connection.execute(
                "UPDATE entity_redirects SET target_entity_id = ? WHERE target_entity_id = ?",
                (target["id"], source["id"]),
            )
            connection.execute("DELETE FROM entity_relationships WHERE source_entity_id = ? OR target_entity_id = ?", (source["id"], source["id"]))
            connection.execute("DELETE FROM entity_mentions WHERE entity_id = ?", (source["id"],))
            connection.execute("DELETE FROM entity_aliases WHERE entity_id = ?", (source["id"],))
            connection.execute("DELETE FROM entities WHERE id = ?", (source["id"],))
            connection.execute(
                """INSERT INTO entity_redirects(source_entity_uid, target_entity_id, redirect_kind, reason)
                   VALUES (?, ?, 'merged', ?)
                   ON CONFLICT(source_entity_uid) DO UPDATE SET
                       target_entity_id = excluded.target_entity_id,
                       redirect_kind = excluded.redirect_kind, reason = excluded.reason""",
                (source_uid, target["id"], reason),
            )
            connection.execute(
                """INSERT INTO entity_identity_operations(
                       event_uid, operation, source_uids_json, result_uids_json,
                       actor, reason
                   ) VALUES (?, 'merge', ?, ?, ?, ?)""",
                (
                    operation_uid, json.dumps([source_uid, target_uid]),
                    json.dumps([target["entity_uid"]]), actor, reason,
                ),
            )
            from shared.merkle import refresh_current_work_knowledge_root

            refresh_current_work_knowledge_root(connection)
            return target["entity_uid"]
    finally:
        connection.close()


def split_entity(
    db_path: str | Path,
    *,
    source_uid: str,
    new_name: str,
    actor: str,
    alias_names: list[str] | None = None,
    new_uid: str | None = None,
    reason: str | None = None,
    event_uid: str | None = None,
    _record_canonical: bool = True,
) -> str:
    result_uid = new_uid or str(uuid.uuid4())
    operation_uid = event_uid or str(uuid.uuid4())
    if event_uid:
        idempotency_connection = connect(db_path, read_only=True)
        try:
            previous = idempotency_connection.execute(
                "SELECT result_uids_json FROM entity_identity_operations WHERE event_uid = ?",
                (operation_uid,),
            ).fetchone()
            if previous:
                return json.loads(previous[0])[-1]
        finally:
            idempotency_connection.close()
    validation_connection = connect(db_path, read_only=True)
    try:
        if resolve_entity_uid(validation_connection, source_uid) is None:
            raise KeyError(f"entidade não encontrada: {source_uid}")
        if validation_connection.execute(
            "SELECT 1 FROM entities WHERE entity_uid = ?", (result_uid,)
        ).fetchone():
            raise ValueError(f"new_uid já existe: {result_uid}")
    finally:
        validation_connection.close()
    if _record_canonical:
        from shared.knowledge_governance import append_identity_operation_event

        append_identity_operation_event(
            db_path,
            {
                "event_uid": operation_uid,
                "event_type": "entity_split",
                "source_uid": source_uid,
                "new_uid": result_uid,
                "new_name": new_name,
                "alias_names": alias_names or [],
                "actor": actor,
                "reason": reason,
            },
        )
    connection = connect(db_path)
    try:
        with transaction(connection):
            previous = connection.execute(
                "SELECT result_uids_json FROM entity_identity_operations WHERE event_uid = ?",
                (operation_uid,),
            ).fetchone()
            if previous:
                return json.loads(previous[0])[-1]
            source = resolve_entity_uid(connection, source_uid)
            if source is None:
                raise KeyError(f"entidade não encontrada: {source_uid}")
            connection.execute(
                """INSERT INTO entities(
                       book_id, entity_type_id, canonical_name, description,
                       entity_uid, universe_entity_uid, authority_source_id
                   ) VALUES (?, ?, ?, ?, ?, NULL, ?)""",
                (
                    source["book_id"], source["entity_type_id"], new_name,
                    source["description"], result_uid, source["authority_source_id"],
                ),
            )
            new_id = connection.execute(
                "SELECT id FROM entities WHERE entity_uid = ?", (result_uid,)
            ).fetchone()[0]
            for alias in alias_names or []:
                connection.execute(
                    "UPDATE entity_aliases SET entity_id = ? WHERE entity_id = ? AND alias = ? COLLATE NOCASE",
                    (new_id, source["id"], alias),
                )
            connection.execute(
                """INSERT INTO entity_identity_operations(
                       event_uid, operation, source_uids_json, result_uids_json,
                       actor, reason
                   ) VALUES (?, 'split', ?, ?, ?, ?)""",
                (
                    operation_uid,
                    json.dumps([source["entity_uid"]]),
                    json.dumps([source["entity_uid"], result_uid]), actor, reason,
                ),
            )
            from shared.merkle import refresh_current_work_knowledge_root

            refresh_current_work_knowledge_root(connection)
            return result_uid
    finally:
        connection.close()
