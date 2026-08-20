"""Consultas de dossiê, relações e linha do tempo de entidades."""

from __future__ import annotations

import json
from pathlib import Path

from shared.db_engine import connect
from shared.search_service import active_document_ids


class EntityNotFoundError(LookupError):
    pass


def _json_value(value: str | None) -> object:
    return json.loads(value) if value is not None else None


def get_entity_dossier(
    db_path: str | Path,
    entity_name: str,
    *,
    up_to_scene_uid: str | None = None,
) -> dict[str, object]:
    """Retorna identidade, aliases, menções, relações, claims e estados."""

    normalized = entity_name.strip()
    if not normalized:
        raise ValueError("entity_name não pode ser vazio")
    connection = connect(db_path, read_only=True)
    try:
        entity = connection.execute(
            """SELECT DISTINCT entity.id, entity.entity_uid,
                      entity.universe_entity_uid, entity.canonical_name,
                      entity.description, type.code AS entity_type
               FROM entities AS entity
               JOIN entity_types AS type ON type.id = entity.entity_type_id
               LEFT JOIN entity_aliases AS alias ON alias.entity_id = entity.id
               WHERE entity.canonical_name = ? COLLATE NOCASE
                  OR alias.alias = ? COLLATE NOCASE
                  OR entity.entity_uid = ?
               ORDER BY CASE WHEN entity.canonical_name = ? COLLATE NOCASE
                             THEN 0 ELSE 1 END, entity.id
               LIMIT 1""",
            (normalized, normalized, normalized, normalized),
        ).fetchone()
        if entity is None:
            entity = connection.execute(
                """SELECT entity.id, entity.entity_uid,
                          entity.universe_entity_uid, entity.canonical_name,
                          entity.description, type.code AS entity_type
                   FROM entity_redirects AS redirect
                   JOIN entities AS entity ON entity.id = redirect.target_entity_id
                   JOIN entity_types AS type ON type.id = entity.entity_type_id
                   WHERE redirect.source_entity_uid = ?""",
                (normalized,),
            ).fetchone()
        if entity is None:
            raise EntityNotFoundError(f"entidade não encontrada: {entity_name}")

        document_ids = active_document_ids(connection)
        placeholders = ",".join("?" for _ in document_ids) or "NULL"
        cutoff: tuple[int, int] | None = None
        if up_to_scene_uid is not None:
            cutoff_row = connection.execute(
                """SELECT chapter.document_id, chapter.ordinal AS chapter_ordinal,
                          scene.ordinal AS scene_ordinal
                   FROM scenes AS scene
                   JOIN chapters AS chapter ON chapter.id = scene.chapter_id
                   WHERE scene.scene_uid = ?""",
                (up_to_scene_uid,),
            ).fetchone()
            if cutoff_row is None:
                raise ValueError(f"scene UID inexistente: {up_to_scene_uid}")
            cutoff = (cutoff_row["chapter_ordinal"], cutoff_row["scene_ordinal"])
            cutoff_document = cutoff_row["document_id"]
        else:
            cutoff_document = None

        aliases = [
            row["alias"]
            for row in connection.execute(
                "SELECT alias FROM entity_aliases WHERE entity_id = ? ORDER BY alias",
                (entity["id"],),
            )
        ]
        mention_rows = connection.execute(
            f"""SELECT document.relative_path, chapter.title AS chapter_title,
                       scene.scene_uid, scene.scene_title, scene.start_line,
                       scene.end_line, mention.surface_form, mention.start_offset,
                       mention.end_offset, mention.confidence,
                       chapter.document_id, chapter.ordinal AS chapter_ordinal,
                       scene.ordinal AS scene_ordinal
                FROM entity_mentions AS mention
                JOIN scenes AS scene ON scene.id = mention.scene_id
                JOIN chapters AS chapter ON chapter.id = scene.chapter_id
                JOIN documents AS document ON document.id = chapter.document_id
                WHERE mention.entity_id = ?
                  AND chapter.document_id IN ({placeholders})
                ORDER BY chapter.document_id, chapter.ordinal, scene.ordinal,
                         mention.start_offset""",
            [entity["id"], *document_ids],
        ).fetchall()
        mentions = []
        for row in mention_rows:
            if cutoff is not None and (
                row["document_id"] != cutoff_document
                or (row["chapter_ordinal"], row["scene_ordinal"]) > cutoff
            ):
                continue
            mentions.append(
                {
                    key: row[key]
                    for key in (
                        "relative_path",
                        "chapter_title",
                        "scene_uid",
                        "scene_title",
                        "surface_form",
                        "start_offset",
                        "end_offset",
                        "confidence",
                    )
                }
            )

        relationships = [
            dict(row)
            for row in connection.execute(
                """SELECT type.code AS relationship,
                          source.entity_uid AS source_uid,
                          source.canonical_name AS source_name,
                          target.entity_uid AS target_uid,
                          target.canonical_name AS target_name,
                          start_scene.scene_uid AS valid_from_scene_uid,
                          end_scene.scene_uid AS valid_to_scene_uid,
                          relation.notes
                   FROM entity_relationships AS relation
                   JOIN relationship_types AS type
                        ON type.id = relation.relationship_type_id
                   JOIN entities AS source ON source.id = relation.source_entity_id
                   JOIN entities AS target ON target.id = relation.target_entity_id
                   LEFT JOIN scenes AS start_scene
                        ON start_scene.id = relation.valid_from_scene_id
                   LEFT JOIN scenes AS end_scene
                        ON end_scene.id = relation.valid_to_scene_id
                   WHERE relation.source_entity_id = ? OR relation.target_entity_id = ?
                   ORDER BY type.code, source.canonical_name, target.canonical_name""",
                (entity["id"], entity["id"]),
            )
        ]

        state_rows = connection.execute(
            f"""SELECT scene.scene_uid, chapter.title AS chapter_title,
                       chapter.document_id, chapter.ordinal AS chapter_ordinal,
                       scene.ordinal AS scene_ordinal, event.event_ordinal,
                       event.summary, attribute.code AS attribute,
                       delta.old_value_json, delta.new_value_json
                FROM entity_state_events AS event
                JOIN scenes AS scene ON scene.id = event.scene_id
                JOIN chapters AS chapter ON chapter.id = scene.chapter_id
                LEFT JOIN entity_state_deltas AS delta ON delta.event_id = event.id
                LEFT JOIN state_attributes AS attribute ON attribute.id = delta.attribute_id
                WHERE event.entity_id = ?
                  AND chapter.document_id IN ({placeholders})
                ORDER BY chapter.document_id, chapter.ordinal, scene.ordinal,
                         event.event_ordinal, attribute.code""",
            [entity["id"], *document_ids],
        ).fetchall()
        events_by_key: dict[tuple[str, int], dict[str, object]] = {}
        for row in state_rows:
            if cutoff is not None and (
                row["document_id"] != cutoff_document
                or (row["chapter_ordinal"], row["scene_ordinal"]) > cutoff
            ):
                continue
            key = (row["scene_uid"], row["event_ordinal"])
            event = events_by_key.setdefault(
                key,
                {
                    "scene_uid": row["scene_uid"],
                    "chapter_title": row["chapter_title"],
                    "event_ordinal": row["event_ordinal"],
                    "summary": row["summary"],
                    "deltas": [],
                },
            )
            if row["attribute"] is not None:
                event["deltas"].append(
                    {
                        "attribute": row["attribute"],
                        "old_value": _json_value(row["old_value_json"]),
                        "new_value": _json_value(row["new_value_json"]),
                    }
                )

        claims = [
            {
                "predicate": row["predicate"],
                "object_entity_uid": row["object_entity_uid"],
                "object_value": _json_value(row["object_value_json"]),
                "scene_uid": row["scene_uid"],
                "canon_level": row["canon_level"],
                "continuity": row["continuity"],
                "confidence": row["confidence"],
                "source_excerpt": row["source_excerpt"],
                "authority": row["authority"],
                "authority_rank": row["authority_rank"],
                "authority_position": row["authority_position"],
            }
            for row in connection.execute(
                """SELECT predicate.code AS predicate,
                          object.entity_uid AS object_entity_uid,
                          claim.object_value_json, scene.scene_uid,
                          canon.code AS canon_level,
                          continuity.code AS continuity, claim.confidence,
                          claim.source_excerpt, authority.code AS authority,
                          ranked.effective_authority_rank AS authority_rank,
                          ranked.authority_position
                   FROM ranked_entity_claims AS ranked
                   JOIN entity_claims AS claim ON claim.id = ranked.id
                   JOIN claim_predicates AS predicate ON predicate.id = claim.predicate_id
                   LEFT JOIN entities AS object ON object.id = claim.object_entity_id
                   JOIN scenes AS scene ON scene.id = claim.asserted_scene_id
                   LEFT JOIN canon_levels AS canon ON canon.id = claim.canon_level_id
                   LEFT JOIN continuity_branches AS continuity
                        ON continuity.id = claim.continuity_id
                   LEFT JOIN authority_sources AS authority
                        ON authority.id = claim.authority_source_id
                   WHERE claim.subject_entity_id = ?
                   ORDER BY scene.id, predicate.code""",
                (entity["id"],),
            )
        ]
        return {
            "entity_uid": entity["entity_uid"],
            "universe_entity_uid": entity["universe_entity_uid"],
            "canonical_name": entity["canonical_name"],
            "entity_type": entity["entity_type"],
            "description": entity["description"],
            "aliases": aliases,
            "mentions": mentions,
            "relationships": relationships,
            "state_timeline": list(events_by_key.values()),
            "claims": claims,
        }
    finally:
        connection.close()
