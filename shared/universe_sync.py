"""Sincronizador explícito entre bancos por livro e o índice do universo."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

from shared.db_engine import connect, database_path, transaction
from shared.universe_db_engine import (
    import_book_merkle_roots,
    initialize_universe_database,
    refresh_universe_merkle_roots,
)


_UNIVERSE_ENTITY_NAMESPACE: Final = uuid.UUID("a51f3d46-fceb-4672-b0ef-27e6e2377ca8")


@dataclass(frozen=True, slots=True)
class UniverseSyncReport:
    works: int
    entities: int
    mappings: int
    relationships: int
    claims: int
    content_merkle_root: str
    knowledge_merkle_root: str


def sync_universe(
    universe_dir: str | Path,
    *,
    universe_uid: str,
    book_dirs: list[str | Path],
    name: str | None = None,
) -> UniverseSyncReport:
    root = Path(universe_dir).expanduser().resolve()
    db_path = initialize_universe_database(
        root, universe_uid=universe_uid, name=name
    )
    universe_connection = connect(db_path)
    entity_count = mapping_count = relationship_count = claim_count = 0
    try:
        with transaction(universe_connection):
            for book_dir_value in book_dirs:
                book_dir = Path(book_dir_value).expanduser().resolve()
                book_db = database_path(book_dir)
                book_connection = connect(book_db, read_only=True)
                try:
                    work = book_connection.execute(
                        "SELECT id, work_uid, title FROM works ORDER BY id LIMIT 1"
                    ).fetchone()
                    if work is None:
                        raise RuntimeError(f"banco sem obra: {book_db}")
                    relative_db = os.path.relpath(book_db, root)
                    universe_connection.execute(
                        """INSERT INTO works(work_uid, title, book_db_relative_path, indexed_at)
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                           ON CONFLICT(work_uid) DO UPDATE SET
                               title = excluded.title,
                               book_db_relative_path = excluded.book_db_relative_path,
                               indexed_at = CURRENT_TIMESTAMP""",
                        (work["work_uid"], work["title"], relative_db),
                    )
                    universe_work_id = universe_connection.execute(
                        "SELECT id FROM works WHERE work_uid = ?", (work["work_uid"],)
                    ).fetchone()[0]
                    universe_connection.execute(
                        "DELETE FROM cross_work_relationships WHERE source_work_id = ?",
                        (universe_work_id,),
                    )
                    universe_connection.execute(
                        "DELETE FROM universe_claims WHERE source_work_id = ?",
                        (universe_work_id,),
                    )
                    work_relationship_count = 0
                    work_claim_count = 0
                    local_to_global: dict[str, int] = {}
                    for local in book_connection.execute(
                        """SELECT entity.entity_uid, entity.universe_entity_uid,
                                  entity.canonical_name, entity.description, type.code
                           FROM entities AS entity
                           JOIN entity_types AS type ON type.id = entity.entity_type_id"""
                    ):
                        global_uid = local["universe_entity_uid"] or str(
                            uuid.uuid5(
                                _UNIVERSE_ENTITY_NAMESPACE,
                                f"{local['code']}:{local['canonical_name'].casefold()}",
                            )
                        )
                        type_id = universe_connection.execute(
                            "SELECT id FROM entity_types WHERE code = ?", (local["code"],)
                        ).fetchone()[0]
                        existing_global = universe_connection.execute(
                            """SELECT id, entity_uid FROM universe_entities
                               WHERE entity_uid = ? OR (
                                   entity_type_id = ? AND canonical_name = ? COLLATE NOCASE
                               ) ORDER BY entity_uid = ? DESC LIMIT 1""",
                            (global_uid, type_id, local["canonical_name"], global_uid),
                        ).fetchone()
                        if existing_global is None:
                            global_id = universe_connection.execute(
                                """INSERT INTO universe_entities(
                                       entity_uid, entity_type_id, canonical_name, description
                                   ) VALUES (?, ?, ?, ?)""",
                                (global_uid, type_id, local["canonical_name"], local["description"]),
                            ).lastrowid
                        else:
                            global_id = existing_global["id"]
                            universe_connection.execute(
                                """UPDATE universe_entities SET
                                       description = COALESCE(?, description),
                                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                                (local["description"], global_id),
                            )
                        mapping_kind = "same_identity" if local["universe_entity_uid"] else "uncertain"
                        mapping_kind_id = universe_connection.execute(
                            "SELECT id FROM mapping_kinds WHERE code = ?", (mapping_kind,)
                        ).fetchone()[0]
                        universe_connection.execute(
                            """INSERT INTO work_entity_mappings(
                                   universe_entity_id, work_id, local_entity_uid,
                                   mapping_kind_id, confidence, evidence_json
                               ) VALUES (?, ?, ?, ?, ?, ?)
                               ON CONFLICT(work_id, local_entity_uid) DO UPDATE SET
                                   universe_entity_id = excluded.universe_entity_id,
                                   mapping_kind_id = excluded.mapping_kind_id,
                                   confidence = excluded.confidence,
                                   evidence_json = excluded.evidence_json,
                                   mapped_at = CURRENT_TIMESTAMP""",
                            (
                                global_id, universe_work_id, local["entity_uid"], mapping_kind_id,
                                1.0 if local["universe_entity_uid"] else 0.5,
                                json.dumps({"method": "explicit_uid" if local["universe_entity_uid"] else "normalized_name"}),
                            ),
                        )
                        entity_count += 1
                        mapping_count += 1
                        local_to_global[local["entity_uid"]] = int(global_id)
                        for alias in book_connection.execute(
                            """SELECT alias FROM entity_aliases
                               WHERE entity_id = (
                                   SELECT id FROM entities WHERE entity_uid = ?
                               )""",
                            (local["entity_uid"],),
                        ):
                            universe_connection.execute(
                                """INSERT OR IGNORE INTO universe_entity_aliases(
                                       entity_id, alias, language
                                   ) VALUES (?, ?, NULL)""",
                                (global_id, alias[0]),
                            )

                    for relation in book_connection.execute(
                        """SELECT relation.id, source.entity_uid AS source_uid,
                                  target.entity_uid AS target_uid, type.code AS type_code,
                                  type.label AS type_label, type.is_symmetric,
                                  relation.notes, scene.scene_uid, scene.start_line,
                                  scene.end_line, scene.content_sha256
                           FROM entity_relationships AS relation
                           JOIN entities AS source ON source.id = relation.source_entity_id
                           JOIN entities AS target ON target.id = relation.target_entity_id
                           JOIN relationship_types AS type ON type.id = relation.relationship_type_id
                           LEFT JOIN scenes AS scene ON scene.id = relation.valid_from_scene_id"""
                    ):
                        if relation["source_uid"] not in local_to_global or relation["target_uid"] not in local_to_global:
                            continue
                        universe_connection.execute(
                            """INSERT INTO relationship_types(code, label, is_symmetric)
                               VALUES (?, ?, ?) ON CONFLICT(code) DO NOTHING""",
                            (relation["type_code"], relation["type_label"], relation["is_symmetric"]),
                        )
                        type_id = universe_connection.execute(
                            "SELECT id FROM relationship_types WHERE code = ?", (relation["type_code"],)
                        ).fetchone()[0]
                        relationship_id = universe_connection.execute(
                            """INSERT INTO cross_work_relationships(
                                   source_entity_id, target_entity_id, relationship_type_id,
                                   confidence, notes, source_work_id,
                                   source_local_relationship_id
                               ) VALUES (?, ?, ?, 1.0, ?, ?, ?)""",
                            (
                                local_to_global[relation["source_uid"]],
                                local_to_global[relation["target_uid"]],
                                type_id, relation["notes"], universe_work_id, relation["id"],
                            ),
                        ).lastrowid
                        if relation["scene_uid"]:
                            universe_connection.execute(
                                """INSERT INTO relationship_sources(
                                       relationship_id, work_id, local_scene_uid,
                                       start_line, end_line, source_sha256,
                                       extraction_method
                                   ) VALUES (?, ?, ?, ?, ?, ?, 'book-sync')""",
                                (
                                    relationship_id, universe_work_id, relation["scene_uid"],
                                    relation["start_line"], relation["end_line"],
                                    relation["content_sha256"],
                                ),
                            )
                        relationship_count += 1
                        work_relationship_count += 1

                    for claim in book_connection.execute(
                        """SELECT claim.id, subject.entity_uid AS subject_uid,
                                  object.entity_uid AS object_uid,
                                  claim.object_value_json, predicate.code AS predicate_code,
                                  predicate.label AS predicate_label, claim.confidence,
                                  claim.source_excerpt, claim.extraction_method,
                                  scene.scene_uid, scene.start_line, scene.end_line,
                                  scene.content_sha256, canon.code AS canon_code,
                                  continuity.code AS continuity_code
                           FROM entity_claims AS claim
                           JOIN entities AS subject ON subject.id = claim.subject_entity_id
                           LEFT JOIN entities AS object ON object.id = claim.object_entity_id
                           JOIN claim_predicates AS predicate ON predicate.id = claim.predicate_id
                           JOIN scenes AS scene ON scene.id = claim.asserted_scene_id
                           LEFT JOIN canon_levels AS canon ON canon.id = claim.canon_level_id
                           LEFT JOIN continuity_branches AS continuity ON continuity.id = claim.continuity_id"""
                    ):
                        if claim["subject_uid"] not in local_to_global:
                            continue
                        object_id = (
                            local_to_global.get(claim["object_uid"]) if claim["object_uid"] else None
                        )
                        if claim["object_uid"] and object_id is None:
                            continue
                        universe_connection.execute(
                            """INSERT INTO claim_predicates(code, label)
                               VALUES (?, ?) ON CONFLICT(code) DO NOTHING""",
                            (claim["predicate_code"], claim["predicate_label"]),
                        )
                        predicate_id = universe_connection.execute(
                            "SELECT id FROM claim_predicates WHERE code = ?", (claim["predicate_code"],)
                        ).fetchone()[0]
                        canon_id = None
                        if claim["canon_code"]:
                            row = universe_connection.execute(
                                "SELECT id FROM canon_levels WHERE code = ?", (claim["canon_code"],)
                            ).fetchone()
                            canon_id = row[0] if row else None
                        continuity_id = None
                        if claim["continuity_code"]:
                            row = universe_connection.execute(
                                "SELECT id FROM continuity_branches WHERE code = ?", (claim["continuity_code"],)
                            ).fetchone()
                            continuity_id = row[0] if row else None
                        universe_claim_id = universe_connection.execute(
                            """INSERT INTO universe_claims(
                                   subject_entity_id, predicate_id, object_entity_id,
                                   object_value_json, continuity_id, canon_level_id,
                                   confidence, source_work_id, source_local_claim_id
                               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                local_to_global[claim["subject_uid"]], predicate_id, object_id,
                                claim["object_value_json"], continuity_id, canon_id,
                                claim["confidence"], universe_work_id, claim["id"],
                            ),
                        ).lastrowid
                        universe_connection.execute(
                            """INSERT INTO claim_sources(
                                   claim_id, work_id, local_scene_uid, start_line,
                                   end_line, source_sha256, source_excerpt,
                                   extraction_method
                               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                universe_claim_id, universe_work_id, claim["scene_uid"],
                                claim["start_line"], claim["end_line"],
                                claim["content_sha256"], claim["source_excerpt"],
                                claim["extraction_method"],
                            ),
                        )
                        claim_count += 1
                        work_claim_count += 1
                finally:
                    book_connection.close()
                imported_roots = import_book_merkle_roots(
                    universe_connection,
                    work_uid=work["work_uid"],
                    book_db_path=book_db,
                )
                universe_connection.execute(
                    """INSERT INTO universe_sync_runs(
                           work_id, source_content_root, entities_count,
                           relationships_count, claims_count
                       ) VALUES (?, ?, ?, ?, ?)""",
                    (
                        universe_work_id, imported_roots.content,
                        len(local_to_global), work_relationship_count, work_claim_count,
                    ),
                )
            roots = refresh_universe_merkle_roots(universe_connection)
        works = universe_connection.execute("SELECT count(*) FROM works").fetchone()[0]
    finally:
        universe_connection.close()
    return UniverseSyncReport(
        works=works,
        entities=entity_count,
        mappings=mapping_count,
        relationships=relationship_count,
        claims=claim_count,
        content_merkle_root=roots.content,
        knowledge_merkle_root=roots.knowledge or "",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Agrega livros em um universo editorial")
    parser.add_argument("universe_dir")
    parser.add_argument("--universe-uid", required=True)
    parser.add_argument("--book", action="append", required=True, dest="books")
    parser.add_argument("--name")
    args = parser.parse_args()
    print(json.dumps(asdict(sync_universe(
        args.universe_dir,
        universe_uid=args.universe_uid,
        book_dirs=args.books,
        name=args.name,
    )), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
