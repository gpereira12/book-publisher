"""Ingestão determinística de conhecimento YAML e menções no manuscrito."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

import yaml

from shared.db_engine import connect, database_path, initialize_book_database, transaction
from shared.knowledge_contract import validate_knowledge_payload
from shared.merkle import hash_node, refresh_work_merkle_roots


_ENTITY_NAMESPACE: Final = uuid.UUID("3d8b64b7-bc8c-4d42-934b-cf81ed89389f")


@dataclass(frozen=True, slots=True)
class KnowledgeSyncReport:
    entities: int
    aliases: int
    mentions: int
    relationships: int
    states: int
    claims: int
    source_sha256: str


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("a raiz do YAML de conhecimento deve ser um mapa")
    return payload


def _normalized_entities(payload: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = payload.get("entities")
    if isinstance(explicit, list):
        return [item for item in explicit if isinstance(item, dict)]
    # Compatibilidade com os dossiês editoriais existentes em português.
    characters = payload.get("personagens", [])
    return [
        {
            "name": item.get("nome"),
            "type": "character",
            "description": item.get("papel"),
            "attributes": {
                key: value
                for key, value in item.items()
                if key not in {"nome", "papel"}
            },
        }
        for item in characters
        if isinstance(item, dict) and item.get("nome")
    ]


def _entity_uid(work_uid: str, item: dict[str, Any]) -> str:
    explicit = item.get("uid")
    if explicit:
        return str(explicit)
    return str(uuid.uuid5(_ENTITY_NAMESPACE, f"{work_uid}:{item.get('type', 'concept')}:{item['name']}"))


def _scene_id(connection, scene_uid: str | None) -> int | None:
    if not scene_uid:
        return None
    row = connection.execute("SELECT id FROM scenes WHERE scene_uid = ?", (scene_uid,)).fetchone()
    if row is None:
        raise KeyError(f"scene_uid não encontrado: {scene_uid}")
    return int(row[0])


def sync_knowledge_yaml(
    book_dir: str | Path,
    *,
    yaml_path: str | Path = "knowledge.yaml",
    authority: str = "editorial_dossier",
    extract_mentions: bool = True,
) -> KnowledgeSyncReport:
    root = Path(book_dir).expanduser().resolve()
    path = Path(yaml_path)
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        relative_path = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("o YAML deve estar dentro da pasta do livro") from exc
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    payload = _load_yaml(path)
    validate_knowledge_payload(payload)
    db_path = initialize_book_database(root)
    connection = connect(db_path)
    counts = dict(entities=0, aliases=0, mentions=0, relationships=0, states=0, claims=0)
    try:
        with transaction(connection):
            authority_row = connection.execute(
                "SELECT id FROM authority_sources WHERE code = ?", (authority,)
            ).fetchone()
            if authority_row is None:
                raise KeyError(f"fonte de autoridade desconhecida: {authority}")
            authority_id = authority_row[0]
            work_uid = connection.execute("SELECT work_uid FROM works ORDER BY id LIMIT 1").fetchone()[0]
            connection.execute(
                "DELETE FROM entity_aliases WHERE extraction_method = 'yaml' AND source_relative_path = ?",
                (relative_path,),
            )
            connection.execute(
                "DELETE FROM entity_relationships WHERE extraction_method = 'yaml' AND source_relative_path = ?",
                (relative_path,),
            )
            connection.execute(
                "DELETE FROM entity_state_events WHERE extraction_method = 'yaml' AND source_relative_path = ?",
                (relative_path,),
            )
            connection.execute(
                "DELETE FROM entity_mentions WHERE extraction_method = 'yaml_exact' AND source_relative_path = ?",
                (relative_path,),
            )
            entities_by_name: dict[str, int] = {}
            for predicate in payload.get("predicates", []) or []:
                code = str(predicate["code"])
                connection.execute(
                    """INSERT INTO claim_predicates(code, label, description)
                       VALUES (?, ?, ?)
                       ON CONFLICT(code) DO UPDATE SET
                           label = excluded.label,
                           description = excluded.description""",
                    (
                        code,
                        predicate.get("label", code.replace("_", " ").title()),
                        predicate.get("description"),
                    ),
                )
                predicate_id = connection.execute(
                    "SELECT id FROM claim_predicates WHERE code = ?", (code,)
                ).fetchone()[0]
                value_kind = str(predicate.get("value_kind", "any"))
                value_kind_id = connection.execute(
                    "SELECT id FROM predicate_value_kinds WHERE code = ?", (value_kind,)
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO claim_predicate_rules(
                           predicate_id, value_kind_id, cardinality, temporal_mode,
                           unit_code, allows_entity_object, allows_literal_object
                       ) VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(predicate_id) DO UPDATE SET
                           value_kind_id = excluded.value_kind_id,
                           cardinality = excluded.cardinality,
                           temporal_mode = excluded.temporal_mode,
                           unit_code = excluded.unit_code,
                           allows_entity_object = excluded.allows_entity_object,
                           allows_literal_object = excluded.allows_literal_object""",
                    (
                        predicate_id,
                        value_kind_id,
                        predicate.get("cardinality", "multiple"),
                        predicate.get("temporal_mode", "timeless"),
                        predicate.get("unit"),
                        int(predicate.get("allows_entity_object", True)),
                        int(predicate.get("allows_literal_object", True)),
                    ),
                )
            for item in _normalized_entities(payload):
                if not item.get("name"):
                    continue
                entity_type = str(item.get("type", "concept"))
                type_row = connection.execute(
                    "SELECT id FROM entity_types WHERE code = ?", (entity_type,)
                ).fetchone()
                if type_row is None:
                    raise KeyError(f"tipo de entidade desconhecido: {entity_type}")
                uid = _entity_uid(work_uid, item)
                connection.execute(
                    """INSERT INTO entities(
                           book_id, entity_type_id, canonical_name, description,
                           entity_uid, universe_entity_uid, authority_source_id
                       ) VALUES (1, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(entity_uid) DO UPDATE SET
                           canonical_name = excluded.canonical_name,
                           description = COALESCE(excluded.description, entities.description),
                           universe_entity_uid = COALESCE(excluded.universe_entity_uid, entities.universe_entity_uid),
                           authority_source_id = excluded.authority_source_id,
                           updated_at = CURRENT_TIMESTAMP""",
                    (
                        type_row[0], item["name"], item.get("description"), uid,
                        item.get("universe_uid"), authority_id,
                    ),
                )
                entity_id = connection.execute(
                    "SELECT id FROM entities WHERE entity_uid = ?", (uid,)
                ).fetchone()[0]
                entities_by_name[str(item["name"]).casefold()] = entity_id
                counts["entities"] += 1
                for alias in item.get("aliases", []) or []:
                    connection.execute(
                        """INSERT OR IGNORE INTO entity_aliases(
                               entity_id, alias, extraction_method, source_relative_path
                           ) VALUES (?, ?, 'yaml', ?)""",
                        (entity_id, str(alias), relative_path),
                    )
                    counts["aliases"] += 1

                attributes = item.get("attributes", {}) or {}
                scene_uid = item.get("state_scene_uid")
                if attributes and scene_uid:
                    scene_id = _scene_id(connection, str(scene_uid))
                    event_id = connection.execute(
                        """INSERT INTO entity_state_events(
                               entity_id, scene_id, event_ordinal, summary,
                               extraction_method, source_relative_path
                           ) VALUES (?, ?, 0, 'Estado importado de YAML', 'yaml', ?)
                           ON CONFLICT(entity_id, scene_id, event_ordinal) DO UPDATE SET
                               summary = excluded.summary,
                               extraction_method = excluded.extraction_method,
                               source_relative_path = excluded.source_relative_path RETURNING id""",
                        (entity_id, scene_id, relative_path),
                    ).fetchone()[0]
                    for code, value in attributes.items():
                        connection.execute(
                            """INSERT INTO state_attributes(entity_type_id, code, label, value_kind)
                               VALUES (?, ?, ?, 'json')
                               ON CONFLICT(entity_type_id, code) DO UPDATE SET label = excluded.label""",
                            (type_row[0], str(code), str(code).replace("_", " ").title()),
                        )
                        attribute_id = connection.execute(
                            "SELECT id FROM state_attributes WHERE entity_type_id = ? AND code = ?",
                            (type_row[0], str(code)),
                        ).fetchone()[0]
                        connection.execute(
                            """INSERT INTO entity_state_deltas(event_id, attribute_id, new_value_json)
                               VALUES (?, ?, ?)
                               ON CONFLICT(event_id, attribute_id) DO UPDATE SET
                                   new_value_json = excluded.new_value_json""",
                            (event_id, attribute_id, json.dumps(value, ensure_ascii=False)),
                        )
                        counts["states"] += 1

            # Inclui entidades já existentes para referências cruzadas no YAML.
            for row in connection.execute("SELECT id, canonical_name FROM entities"):
                entities_by_name.setdefault(row["canonical_name"].casefold(), row["id"])

            for item in payload.get("relationships", []) or []:
                source = entities_by_name[str(item["source"]).casefold()]
                target = entities_by_name[str(item["target"]).casefold()]
                type_code = str(item.get("type", "related_to"))
                connection.execute(
                    """INSERT INTO relationship_types(code, label, is_symmetric)
                       VALUES (?, ?, 0) ON CONFLICT(code) DO NOTHING""",
                    (type_code, type_code.replace("_", " ").title()),
                )
                type_id = connection.execute(
                    "SELECT id FROM relationship_types WHERE code = ?", (type_code,)
                ).fetchone()[0]
                from_scene = _scene_id(connection, item.get("from_scene_uid"))
                exists = connection.execute(
                    """SELECT id FROM entity_relationships
                       WHERE source_entity_id = ? AND target_entity_id = ?
                         AND relationship_type_id = ?
                         AND valid_from_scene_id IS ?""",
                    (source, target, type_id, from_scene),
                ).fetchone()
                if exists is None:
                    connection.execute(
                        """INSERT INTO entity_relationships(
                               source_entity_id, target_entity_id, relationship_type_id,
                               valid_from_scene_id, notes, extraction_method,
                               source_relative_path
                           ) VALUES (?, ?, ?, ?, ?, 'yaml', ?)""",
                        (source, target, type_id, from_scene, item.get("notes"), relative_path),
                    )
                counts["relationships"] += 1

            connection.execute(
                """DELETE FROM entity_claims
                   WHERE id IN (
                       SELECT claim_id FROM knowledge_source_claims WHERE relative_path = ?
                   )""",
                (relative_path,),
            )
            for item in payload.get("claims", []) or []:
                subject = entities_by_name[str(item["subject"]).casefold()]
                predicate = str(item["predicate"])
                connection.execute(
                    """INSERT INTO claim_predicates(code, label)
                       VALUES (?, ?) ON CONFLICT(code) DO NOTHING""",
                    (predicate, predicate.replace("_", " ").title()),
                )
                predicate_id = connection.execute(
                    "SELECT id FROM claim_predicates WHERE code = ?", (predicate,)
                ).fetchone()[0]
                object_entity = item.get("object_entity")
                object_id = (
                    entities_by_name[str(object_entity).casefold()] if object_entity else None
                )
                value_json = None if object_id else json.dumps(item.get("value"), ensure_ascii=False)
                scene_id = _scene_id(connection, str(item["scene_uid"]))
                valid_from_scene_id = _scene_id(connection, item.get("valid_from_scene_uid"))
                valid_to_scene_id = _scene_id(connection, item.get("valid_to_scene_uid"))
                rule = connection.execute(
                    """SELECT kind.code, rule.allows_entity_object,
                              rule.allows_literal_object
                       FROM claim_predicate_rules AS rule
                       JOIN predicate_value_kinds AS kind ON kind.id = rule.value_kind_id
                       WHERE rule.predicate_id = ?""",
                    (predicate_id,),
                ).fetchone()
                if rule:
                    if object_id is not None and not rule["allows_entity_object"]:
                        raise ValueError(f"predicado {predicate} não aceita objeto-entidade")
                    if object_id is None and not rule["allows_literal_object"]:
                        raise ValueError(f"predicado {predicate} não aceita valor literal")
                    literal = item.get("value")
                    expected = rule["code"]
                    valid_type = (
                        expected == "any"
                        or (expected == "date" and isinstance(literal, str))
                        or (expected == "text" and isinstance(literal, str))
                        or (expected == "number" and isinstance(literal, (int, float)) and not isinstance(literal, bool))
                        or (expected == "boolean" and isinstance(literal, bool))
                        or (expected == "entity" and object_id is not None)
                    )
                    if not valid_type:
                        raise ValueError(f"valor incompatível com {predicate}: esperado {expected}")
                claim_id = connection.execute(
                    """INSERT INTO entity_claims(
                           subject_entity_id, predicate_id, object_entity_id,
                           object_value_json, asserted_scene_id, confidence,
                           extraction_method, source_excerpt, authority_source_id,
                           valid_from_scene_id, valid_to_scene_id
                       ) VALUES (?, ?, ?, ?, ?, ?, 'yaml', ?, ?, ?, ?)""",
                    (
                        subject, predicate_id, object_id, value_json, scene_id,
                        float(item.get("confidence", 1.0)), item.get("excerpt"), authority_id,
                        valid_from_scene_id, valid_to_scene_id,
                    ),
                ).lastrowid
                connection.execute(
                    "INSERT INTO knowledge_source_claims(relative_path, claim_id) VALUES (?, ?)",
                    (relative_path, claim_id),
                )
                counts["claims"] += 1

            if extract_mentions:
                active_scenes = connection.execute(
                    """SELECT scene.id, scene.content
                       FROM scenes AS scene
                       JOIN chapters AS chapter ON chapter.id = scene.chapter_id
                       JOIN edition_document_assignments AS assignment
                            ON assignment.document_id = chapter.document_id
                       WHERE assignment.is_active = 1"""
                ).fetchall()
                aliases: list[tuple[int, str]] = []
                for row in connection.execute(
                    """SELECT id, canonical_name FROM entities
                       UNION ALL
                       SELECT entity_id, alias FROM entity_aliases"""
                ):
                    aliases.append((row[0], row[1]))
                for scene in active_scenes:
                    for entity_id, surface in aliases:
                        pattern = re.compile(rf"(?<!\w){re.escape(surface)}(?!\w)", re.IGNORECASE)
                        for match in pattern.finditer(scene["content"]):
                            connection.execute(
                                """INSERT OR IGNORE INTO entity_mentions(
                                       entity_id, scene_id, start_offset, end_offset,
                                       surface_form, confidence, extraction_method,
                                       source_relative_path
                                   ) VALUES (?, ?, ?, ?, ?, 1.0, 'yaml_exact', ?)""",
                                (
                                    entity_id, scene["id"], match.start(), match.end(),
                                    match.group(0), relative_path,
                                ),
                            )
                            counts["mentions"] += 1

            connection.execute(
                """INSERT INTO knowledge_ingestion_runs(
                       relative_path, content_sha256, status, entities_count, claims_count
                   ) VALUES (?, ?, 'completed', ?, ?)""",
                (relative_path, digest, counts["entities"], counts["claims"]),
            )
            edition_id = connection.execute(
                "SELECT id FROM editions WHERE is_working_edition = 1 ORDER BY id LIMIT 1"
            ).fetchone()[0]
            config_row = connection.execute(
                """SELECT root.config_hash
                   FROM work_merkle_roots AS root
                   JOIN merkle_root_kinds AS kind ON kind.id = root.root_kind_id
                   JOIN editions AS edition ON edition.work_id = root.work_id
                   WHERE edition.id = ? AND kind.code = 'materialization'""",
                (edition_id,),
            ).fetchone()
            refresh_work_merkle_roots(
                connection,
                edition_id,
                config_hash=(config_row[0] if config_row and config_row[0] else hash_node("parser-config-empty")),
            )
    finally:
        connection.close()
    return KnowledgeSyncReport(source_sha256=digest, **counts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingere conhecimento YAML no índice do livro")
    parser.add_argument("book_dir")
    parser.add_argument("--yaml", default="knowledge.yaml")
    parser.add_argument("--no-mentions", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = sync_knowledge_yaml(args.book_dir, yaml_path=args.yaml, extract_mentions=not args.no_mentions)
    payload = asdict(report)
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload)


if __name__ == "__main__":
    main()
