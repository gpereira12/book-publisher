"""Merkle DAG editorial com separação criptográfica de domínios.

Roots de conteúdo não dependem de títulos, linhas ou chunking. Roots de
estrutura representam identidade e ordem. Roots de materialização incluem a
configuração do parser. Isso permite invalidar somente o que realmente mudou.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final


HASH_ALGORITHM_CODE: Final = "sha256-domain-v1"
_VALID_ROOT_TABLES: Final = frozenset(
    {
        "passage_merkle_roots",
        "scene_merkle_roots",
        "chapter_merkle_roots",
        "document_merkle_roots",
        "work_merkle_roots",
    }
)


@dataclass(frozen=True, slots=True)
class MerkleRootSet:
    content: str
    structure: str
    materialization: str
    knowledge: str | None = None


def canonicalize_json_text(value: str | None) -> str | None:
    """Normaliza JSON semanticamente, preservando ``NULL`` como ausência."""

    if value is None:
        return None
    return json.dumps(
        json.loads(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def hash_node(kind: str, *parts: str | bytes | int | float | bool | None) -> str:
    """Calcula SHA-256 com domínio e partes prefixadas por tamanho.

    O prefixo evita ambiguidades como ``("ab", "c")`` versus ``("a", "bc")``.
    ``None`` é diferente de string vazia.
    """

    digest = hashlib.sha256()
    domain = f"editorial-merkle:{kind}:v1".encode("utf-8")
    digest.update(len(domain).to_bytes(8, "big"))
    digest.update(domain)
    for part in parts:
        if part is None:
            encoded = b"\xff"
        elif isinstance(part, bytes):
            encoded = b"b" + part
        elif isinstance(part, bool):
            encoded = b"t1" if part else b"t0"
        elif isinstance(part, int):
            encoded = b"i" + str(part).encode("ascii")
        elif isinstance(part, float):
            encoded = b"f" + part.hex().encode("ascii")
        else:
            encoded = b"s" + part.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _root_ids(connection: sqlite3.Connection) -> tuple[int, dict[str, int]]:
    algorithm = connection.execute(
        "SELECT id FROM hash_algorithms WHERE code = ?", (HASH_ALGORITHM_CODE,)
    ).fetchone()
    if algorithm is None:
        raise RuntimeError(f"algoritmo Merkle não registrado: {HASH_ALGORITHM_CODE}")
    kinds = {
        row["code"]: row["id"]
        for row in connection.execute("SELECT id, code FROM merkle_root_kinds")
    }
    return algorithm["id"], kinds


def _upsert_root(
    connection: sqlite3.Connection,
    *,
    table: str,
    owner_column: str,
    owner_id: int,
    kind_id: int,
    algorithm_id: int,
    root_hash: str,
    config_hash: str | None = None,
    source_sha256: str | None = None,
) -> None:
    if table not in _VALID_ROOT_TABLES:
        raise ValueError(f"tabela de roots não permitida: {table}")
    columns = [owner_column, "root_kind_id", "algorithm_id", "root_hash"]
    values: list[object] = [owner_id, kind_id, algorithm_id, root_hash]
    if source_sha256 is not None:
        columns.append("source_sha256")
        values.append(source_sha256)
    if table != "passage_merkle_roots":
        columns.append("config_hash")
        values.append(config_hash)
    placeholders = ", ".join("?" for _ in values)
    updates = [
        "algorithm_id = excluded.algorithm_id",
        "root_hash = excluded.root_hash",
        "computed_at = CASE WHEN root_hash <> excluded.root_hash THEN CURRENT_TIMESTAMP ELSE computed_at END",
    ]
    if source_sha256 is not None:
        updates.append("source_sha256 = excluded.source_sha256")
    if table != "passage_merkle_roots":
        updates.append("config_hash = excluded.config_hash")
    connection.execute(
        f"""INSERT INTO {table}({', '.join(columns)}) VALUES ({placeholders})
            ON CONFLICT({owner_column}, root_kind_id) DO UPDATE SET {', '.join(updates)}""",
        values,
    )


def _aggregate(kind: str, roots: Iterable[str]) -> str:
    return hash_node(kind, *roots)


def _knowledge_row_hashes(connection: sqlite3.Connection) -> list[str]:
    """Produz folhas canônicas para o conhecimento local do livro."""

    queries = (
        (
            "knowledge-entity",
            """SELECT e.entity_uid, t.code, e.universe_entity_uid,
                      e.canonical_name, e.description, authority.code
               FROM entities AS e JOIN entity_types AS t ON t.id = e.entity_type_id
               LEFT JOIN authority_sources AS authority
                    ON authority.id = e.authority_source_id""",
        ),
        (
            "knowledge-alias",
            """SELECT e.entity_uid, a.alias, a.extraction_method,
                      a.source_relative_path
               FROM entity_aliases AS a JOIN entities AS e ON e.id = a.entity_id""",
        ),
        (
            "knowledge-mention",
            """SELECT entity.entity_uid, scene.scene_uid, mention.start_offset,
                      mention.end_offset, mention.surface_form, mention.confidence,
                      mention.extraction_method, mention.source_relative_path
               FROM entity_mentions AS mention
               JOIN entities AS entity ON entity.id = mention.entity_id
               JOIN scenes AS scene ON scene.id = mention.scene_id""",
        ),
        (
            "knowledge-relationship",
            """SELECT source.entity_uid, target.entity_uid, rt.code,
                      start_scene.scene_uid, end_scene.scene_uid, rel.notes,
                      rel.extraction_method, rel.source_relative_path
               FROM entity_relationships AS rel
               JOIN entities AS source ON source.id = rel.source_entity_id
               JOIN entities AS target ON target.id = rel.target_entity_id
               JOIN relationship_types AS rt ON rt.id = rel.relationship_type_id
               LEFT JOIN scenes AS start_scene ON start_scene.id = rel.valid_from_scene_id
               LEFT JOIN scenes AS end_scene ON end_scene.id = rel.valid_to_scene_id""",
        ),
        (
            "knowledge-scene-link",
            """SELECT source.scene_uid, target.scene_uid, kind.code,
                      link.weight, link.description, link.provenance_kind
               FROM scene_links AS link
               JOIN scenes AS source ON source.id = link.source_scene_id
               JOIN scenes AS target ON target.id = link.target_scene_id
               JOIN scene_link_types AS kind ON kind.id = link.scene_link_type_id""",
        ),
        (
            "knowledge-entity-redirect",
            """SELECT redirect.source_entity_uid, target.entity_uid,
                      redirect.redirect_kind, redirect.reason
               FROM entity_redirects AS redirect
               JOIN entities AS target ON target.id = redirect.target_entity_id""",
        ),
        (
            "knowledge-predicate-rule",
            """SELECT predicate.code, kind.code, rule.cardinality,
                      rule.temporal_mode, rule.unit_code,
                      rule.allows_entity_object, rule.allows_literal_object
               FROM claim_predicate_rules AS rule
               JOIN claim_predicates AS predicate ON predicate.id = rule.predicate_id
               JOIN predicate_value_kinds AS kind ON kind.id = rule.value_kind_id""",
        ),
        (
            "knowledge-state-event",
            """SELECT entity.entity_uid, scene.scene_uid, event.event_ordinal,
                      event.summary, event.extraction_method,
                      event.source_relative_path
               FROM entity_state_events AS event
               JOIN entities AS entity ON entity.id = event.entity_id
               JOIN scenes AS scene ON scene.id = event.scene_id""",
        ),
        (
            "knowledge-state-delta",
            """SELECT entity.entity_uid, scene.scene_uid, event.event_ordinal,
                      attribute.code, delta.old_value_json, delta.new_value_json
               FROM entity_state_deltas AS delta
               JOIN entity_state_events AS event ON event.id = delta.event_id
               JOIN entities AS entity ON entity.id = event.entity_id
               JOIN scenes AS scene ON scene.id = event.scene_id
               JOIN state_attributes AS attribute ON attribute.id = delta.attribute_id""",
        ),
        (
            "knowledge-claim",
            """SELECT subject.entity_uid, predicate.code, object.entity_uid,
                      claim.object_value_json, scene.scene_uid, canon.code,
                      continuity.code, claim.confidence, claim.extraction_method,
                      claim.source_excerpt, authority.code, authority.authority_rank,
                      valid_from.scene_uid, valid_to.scene_uid,
                      claim.supersedes_claim_id IS NOT NULL
               FROM entity_claims AS claim
               JOIN entities AS subject ON subject.id = claim.subject_entity_id
               JOIN claim_predicates AS predicate ON predicate.id = claim.predicate_id
               LEFT JOIN entities AS object ON object.id = claim.object_entity_id
               JOIN scenes AS scene ON scene.id = claim.asserted_scene_id
               LEFT JOIN canon_levels AS canon ON canon.id = claim.canon_level_id
               LEFT JOIN continuity_branches AS continuity ON continuity.id = claim.continuity_id
               LEFT JOIN authority_sources AS authority
                    ON authority.id = claim.authority_source_id
               LEFT JOIN scenes AS valid_from ON valid_from.id = claim.valid_from_scene_id
               LEFT JOIN scenes AS valid_to ON valid_to.id = claim.valid_to_scene_id""",
        ),
        (
            "knowledge-approved-proposal",
            """SELECT proposal.proposal_uid, proposal.proposal_kind,
                      proposal.payload_json, proposal.source_scene_uid,
                      proposal.extraction_method, proposal.model_name,
                      proposal.model_config_hash, proposal.prompt_hash,
                      proposal.confidence
               FROM knowledge_proposals AS proposal
               JOIN approval_statuses AS status ON status.id = proposal.status_id
               WHERE status.code = 'approved'""",
        ),
    )
    leaves: list[str] = []
    for domain, query in queries:
        for row in connection.execute(query):
            values = list(row)
            if domain == "knowledge-state-delta":
                values[4] = canonicalize_json_text(values[4])
                values[5] = canonicalize_json_text(values[5])
            elif domain == "knowledge-claim":
                values[3] = canonicalize_json_text(values[3])
            elif domain == "knowledge-approved-proposal":
                values[2] = canonicalize_json_text(values[2])
            leaves.append(hash_node(domain, *values))
    return sorted(leaves)


def refresh_document_merkle_roots(
    connection: sqlite3.Connection,
    document_id: int,
    *,
    parser_signature: str,
) -> MerkleRootSet:
    """Recalcula roots de passage até obra dentro da transação corrente."""

    algorithm_id, kinds = _root_ids(connection)
    config_hash = hash_node("materialization-config", parser_signature)
    chapters = connection.execute(
        "SELECT * FROM chapters WHERE document_id = ? ORDER BY ordinal, id",
        (document_id,),
    ).fetchall()
    document_content_roots: list[str] = []
    document_structure_parts: list[str] = []
    document_materialization_roots: list[str] = []

    for chapter in chapters:
        scenes = connection.execute(
            "SELECT * FROM scenes WHERE chapter_id = ? ORDER BY ordinal, id",
            (chapter["id"],),
        ).fetchall()
        chapter_content_roots: list[str] = []
        chapter_structure_parts: list[str] = []
        chapter_materialization_roots: list[str] = []
        for scene in scenes:
            passages = connection.execute(
                "SELECT * FROM passages WHERE scene_id = ? ORDER BY ordinal, id",
                (scene["id"],),
            ).fetchall()
            passage_content_roots: list[str] = []
            passage_materialization_parts: list[str] = []
            for passage in passages:
                passage_content_root = hash_node(
                    "passage-content", passage["content_sha256"]
                )
                passage_materialization_root = hash_node(
                    "passage-materialization",
                    passage_content_root,
                    passage["start_offset"],
                    passage["end_offset"],
                    config_hash,
                )
                _upsert_root(
                    connection,
                    table="passage_merkle_roots",
                    owner_column="passage_id",
                    owner_id=passage["id"],
                    kind_id=kinds["content"],
                    algorithm_id=algorithm_id,
                    root_hash=passage_content_root,
                    source_sha256=passage["content_sha256"],
                )
                _upsert_root(
                    connection,
                    table="passage_merkle_roots",
                    owner_column="passage_id",
                    owner_id=passage["id"],
                    kind_id=kinds["materialization"],
                    algorithm_id=algorithm_id,
                    root_hash=passage_materialization_root,
                    source_sha256=passage["content_sha256"],
                )
                passage_content_roots.append(passage_content_root)
                passage_materialization_parts.append(passage_materialization_root)

            # Conteúdo da cena é independente do algoritmo de chunking.
            scene_content_root = hash_node("scene-content", scene["content_sha256"])
            scene_structure_root = hash_node(
                "scene-structure", scene["scene_uid"], scene["scene_title"]
            )
            scene_materialization_root = hash_node(
                "scene-materialization",
                scene_content_root,
                config_hash,
                *passage_materialization_parts,
            )
            for code, root in (
                ("content", scene_content_root),
                ("structure", scene_structure_root),
                ("materialization", scene_materialization_root),
            ):
                _upsert_root(
                    connection,
                    table="scene_merkle_roots",
                    owner_column="scene_id",
                    owner_id=scene["id"],
                    kind_id=kinds[code],
                    algorithm_id=algorithm_id,
                    root_hash=root,
                    config_hash=config_hash if code == "materialization" else None,
                    source_sha256=scene["content_sha256"],
                )
            chapter_content_roots.append(scene_content_root)
            chapter_structure_parts.extend([scene["scene_uid"], scene_structure_root])
            chapter_materialization_roots.append(scene_materialization_root)

        chapter_content_root = _aggregate("chapter-content", chapter_content_roots)
        chapter_structure_root = hash_node(
            "chapter-structure",
            chapter["chapter_uid"],
            chapter["title"],
            *chapter_structure_parts,
        )
        chapter_materialization_root = hash_node(
            "chapter-materialization",
            chapter_content_root,
            config_hash,
            *chapter_materialization_roots,
        )
        for code, root in (
            ("content", chapter_content_root),
            ("structure", chapter_structure_root),
            ("materialization", chapter_materialization_root),
        ):
            _upsert_root(
                connection,
                table="chapter_merkle_roots",
                owner_column="chapter_id",
                owner_id=chapter["id"],
                kind_id=kinds[code],
                algorithm_id=algorithm_id,
                root_hash=root,
                config_hash=config_hash if code == "materialization" else None,
            )
        document_content_roots.append(chapter_content_root)
        document_structure_parts.extend([chapter["chapter_uid"], chapter_structure_root])
        document_materialization_roots.append(chapter_materialization_root)

    document = connection.execute(
        "SELECT relative_path, edition_id FROM documents WHERE id = ?", (document_id,)
    ).fetchone()
    if document is None:
        raise KeyError(f"documento inexistente: {document_id}")
    document_content_root = _aggregate("document-content", document_content_roots)
    document_structure_root = hash_node(
        "document-structure", document["relative_path"], *document_structure_parts
    )
    document_materialization_root = hash_node(
        "document-materialization",
        document_content_root,
        config_hash,
        *document_materialization_roots,
    )
    for code, root in (
        ("content", document_content_root),
        ("structure", document_structure_root),
        ("materialization", document_materialization_root),
    ):
        _upsert_root(
            connection,
            table="document_merkle_roots",
            owner_column="document_id",
            owner_id=document_id,
            kind_id=kinds[code],
            algorithm_id=algorithm_id,
            root_hash=root,
            config_hash=config_hash if code == "materialization" else None,
        )

    refresh_work_merkle_roots(connection, document["edition_id"], config_hash=config_hash)
    return MerkleRootSet(
        content=document_content_root,
        structure=document_structure_root,
        materialization=document_materialization_root,
    )


def refresh_work_merkle_roots(
    connection: sqlite3.Connection,
    edition_id: int,
    *,
    config_hash: str,
) -> MerkleRootSet:
    algorithm_id, kinds = _root_ids(connection)
    edition = connection.execute(
        "SELECT work_id FROM editions WHERE id = ?", (edition_id,)
    ).fetchone()
    if edition is None:
        raise KeyError(f"edição inexistente: {edition_id}")
    work_id = edition["work_id"]
    rows = connection.execute(
        """WITH active_documents AS (
               SELECT d.id, d.relative_path, assignment.edition_id,
                      role.context_priority,
                      max(role.context_priority) OVER (
                          PARTITION BY edition.work_id
                      ) AS selected_priority
               FROM documents AS d
               JOIN edition_document_assignments AS assignment
                    ON assignment.document_id = d.id AND assignment.is_active = 1
               JOIN document_roles AS role ON role.id = assignment.document_role_id
               JOIN editions AS edition ON edition.id = assignment.edition_id
               WHERE edition.work_id = ? AND role.is_manuscript = 1
           )
           SELECT d.relative_path, kind.code, root.root_hash
           FROM active_documents AS d
           JOIN document_merkle_roots AS root ON root.document_id = d.id
           JOIN merkle_root_kinds AS kind ON kind.id = root.root_kind_id
           WHERE d.context_priority = d.selected_priority
           ORDER BY d.relative_path, kind.code""",
        (work_id,),
    ).fetchall()
    by_kind: dict[str, list[str]] = {"content": [], "structure": [], "materialization": []}
    for row in rows:
        if row["code"] in by_kind:
            by_kind[row["code"]].extend([row["relative_path"], row["root_hash"]])
    content_root = hash_node("work-content", *by_kind["content"])
    structure_root = hash_node("work-structure", *by_kind["structure"])
    materialization_root = hash_node(
        "work-materialization", config_hash, *by_kind["materialization"]
    )
    knowledge_root = _aggregate("work-knowledge", _knowledge_row_hashes(connection))
    for code, root in (
        ("content", content_root),
        ("structure", structure_root),
        ("materialization", materialization_root),
        ("knowledge", knowledge_root),
    ):
        _upsert_root(
            connection,
            table="work_merkle_roots",
            owner_column="work_id",
            owner_id=work_id,
            kind_id=kinds[code],
            algorithm_id=algorithm_id,
            root_hash=root,
            config_hash=config_hash if code == "materialization" else None,
        )
    return MerkleRootSet(content_root, structure_root, materialization_root, knowledge_root)


def refresh_current_work_knowledge_root(
    connection: sqlite3.Connection,
) -> MerkleRootSet:
    """Atualiza conhecimento preservando a configuração de materialização."""

    edition = connection.execute(
        "SELECT id, work_id FROM editions WHERE is_working_edition = 1 ORDER BY id LIMIT 1"
    ).fetchone()
    if edition is None:
        raise RuntimeError("edição de trabalho inexistente")
    config = connection.execute(
        """SELECT root.config_hash
           FROM work_merkle_roots AS root
           JOIN merkle_root_kinds AS kind ON kind.id = root.root_kind_id
           WHERE root.work_id = ? AND kind.code = 'materialization'""",
        (edition["work_id"],),
    ).fetchone()
    config_hash = config[0] if config and config[0] else hash_node("parser-config-empty")
    return refresh_work_merkle_roots(
        connection, edition["id"], config_hash=config_hash
    )
