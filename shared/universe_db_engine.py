"""Índice derivado para conexões entre obras de um mesmo universo editorial.

O banco de universo guarda identidades globais, cronologia, relações e
proveniência. Texto integral, passages e embeddings permanecem nos bancos dos
livros. Não há foreign keys entre arquivos SQLite: os vínculos externos usam
UIDs opacos e são auditados pelo sincronizador.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Final

from shared.db_engine import DatabaseSettings, SchemaVersionError, connect, transaction
from shared.merkle import (
    HASH_ALGORITHM_CODE,
    MerkleRootSet,
    canonicalize_json_text,
    hash_node,
)


UNIVERSE_DB_FILENAME: Final = ".universe_index.db"
LATEST_UNIVERSE_SCHEMA_VERSION: Final = 3


UNIVERSE_MIGRATION_001 = r"""
CREATE TABLE schema_migrations (
    version        INTEGER PRIMARY KEY,
    description    TEXT NOT NULL,
    applied_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE universes (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    universe_uid    TEXT NOT NULL UNIQUE,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    canonical_root  TEXT NOT NULL,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE works (
    id                      INTEGER PRIMARY KEY,
    work_uid                TEXT NOT NULL UNIQUE,
    title                   TEXT NOT NULL,
    book_db_relative_path   TEXT,
    source_content_sha256   TEXT CHECK (
        source_content_sha256 IS NULL OR length(source_content_sha256) = 64
    ),
    indexed_at              TEXT,
    UNIQUE (book_db_relative_path)
) STRICT;

CREATE TABLE entity_types (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT
) STRICT;

CREATE TABLE universe_entities (
    id                  INTEGER PRIMARY KEY,
    entity_uid          TEXT NOT NULL UNIQUE,
    entity_type_id      INTEGER NOT NULL REFERENCES entity_types(id),
    canonical_name      TEXT NOT NULL COLLATE NOCASE,
    description         TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (entity_type_id, canonical_name)
) STRICT;

CREATE TABLE universe_entity_aliases (
    id          INTEGER PRIMARY KEY,
    entity_id   INTEGER NOT NULL REFERENCES universe_entities(id) ON DELETE CASCADE,
    alias       TEXT NOT NULL COLLATE NOCASE,
    language    TEXT,
    notes       TEXT,
    UNIQUE (entity_id, alias, language)
) STRICT;

CREATE TABLE mapping_kinds (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT
) STRICT;

CREATE TABLE work_entity_mappings (
    universe_entity_id  INTEGER NOT NULL REFERENCES universe_entities(id) ON DELETE CASCADE,
    work_id             INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    local_entity_uid    TEXT NOT NULL,
    mapping_kind_id     INTEGER NOT NULL REFERENCES mapping_kinds(id),
    confidence          REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    evidence_json       TEXT CHECK (evidence_json IS NULL OR json_valid(evidence_json)),
    mapped_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (work_id, local_entity_uid),
    UNIQUE (universe_entity_id, work_id, local_entity_uid)
) STRICT, WITHOUT ROWID;

CREATE INDEX idx_work_entity_mappings_global
    ON work_entity_mappings(universe_entity_id, work_id);

CREATE TABLE canon_levels (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    authority_rank  INTEGER NOT NULL UNIQUE CHECK (authority_rank >= 0),
    description     TEXT
) STRICT;

CREATE TABLE continuity_branches (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    description     TEXT,
    is_default      INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1))
) STRICT;

CREATE UNIQUE INDEX idx_universe_continuity_single_default
    ON continuity_branches(is_default) WHERE is_default = 1;

CREATE TABLE relationship_types (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    is_symmetric    INTEGER NOT NULL DEFAULT 0 CHECK (is_symmetric IN (0, 1)),
    description     TEXT
) STRICT;

CREATE TABLE cross_work_relationships (
    id                      INTEGER PRIMARY KEY,
    source_entity_id        INTEGER NOT NULL REFERENCES universe_entities(id) ON DELETE CASCADE,
    target_entity_id        INTEGER NOT NULL REFERENCES universe_entities(id) ON DELETE CASCADE,
    relationship_type_id    INTEGER NOT NULL REFERENCES relationship_types(id),
    continuity_id           INTEGER REFERENCES continuity_branches(id),
    canon_level_id          INTEGER REFERENCES canon_levels(id),
    valid_from_event_uid    TEXT,
    valid_to_event_uid      TEXT,
    confidence              REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    notes                   TEXT,
    CHECK (source_entity_id <> target_entity_id)
) STRICT;

CREATE INDEX idx_cross_relationships_source
    ON cross_work_relationships(source_entity_id, relationship_type_id);
CREATE INDEX idx_cross_relationships_target
    ON cross_work_relationships(target_entity_id, relationship_type_id);

CREATE TABLE relationship_sources (
    relationship_id INTEGER NOT NULL REFERENCES cross_work_relationships(id) ON DELETE CASCADE,
    work_id         INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    local_scene_uid TEXT NOT NULL,
    start_line      INTEGER CHECK (start_line IS NULL OR start_line >= 1),
    end_line        INTEGER CHECK (
        end_line IS NULL OR (start_line IS NOT NULL AND end_line >= start_line)
    ),
    source_sha256   TEXT CHECK (source_sha256 IS NULL OR length(source_sha256) = 64),
    source_excerpt  TEXT,
    extraction_method TEXT NOT NULL,
    PRIMARY KEY (relationship_id, work_id, local_scene_uid)
) STRICT, WITHOUT ROWID;

CREATE TABLE calendars (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT
) STRICT;

CREATE TABLE timeline_events (
    id                  INTEGER PRIMARY KEY,
    event_uid           TEXT NOT NULL UNIQUE,
    continuity_id       INTEGER REFERENCES continuity_branches(id),
    calendar_id         INTEGER REFERENCES calendars(id),
    label               TEXT NOT NULL,
    summary             TEXT,
    chronology_sort_key REAL,
    date_label          TEXT,
    date_precision      TEXT CHECK (
        date_precision IS NULL OR date_precision IN (
            'exact', 'approximate', 'range', 'relative', 'unknown'
        )
    )
) STRICT;

CREATE INDEX idx_timeline_events_order
    ON timeline_events(continuity_id, chronology_sort_key);

CREATE TABLE event_participants (
    event_id        INTEGER NOT NULL REFERENCES timeline_events(id) ON DELETE CASCADE,
    entity_id       INTEGER NOT NULL REFERENCES universe_entities(id) ON DELETE CASCADE,
    role            TEXT,
    PRIMARY KEY (event_id, entity_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE event_locations (
    event_id        INTEGER NOT NULL REFERENCES timeline_events(id) ON DELETE CASCADE,
    entity_id       INTEGER NOT NULL REFERENCES universe_entities(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, entity_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE event_precedence_types (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL
) STRICT;

CREATE TABLE event_precedence (
    earlier_event_id    INTEGER NOT NULL REFERENCES timeline_events(id) ON DELETE CASCADE,
    later_event_id      INTEGER NOT NULL REFERENCES timeline_events(id) ON DELETE CASCADE,
    precedence_type_id  INTEGER NOT NULL REFERENCES event_precedence_types(id),
    confidence          REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    CHECK (earlier_event_id <> later_event_id),
    PRIMARY KEY (earlier_event_id, later_event_id, precedence_type_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE event_sources (
    id              INTEGER PRIMARY KEY,
    event_id        INTEGER NOT NULL REFERENCES timeline_events(id) ON DELETE CASCADE,
    work_id         INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    local_scene_uid TEXT NOT NULL,
    start_line      INTEGER CHECK (start_line IS NULL OR start_line >= 1),
    end_line        INTEGER CHECK (
        end_line IS NULL OR (start_line IS NOT NULL AND end_line >= start_line)
    ),
    source_sha256   TEXT CHECK (source_sha256 IS NULL OR length(source_sha256) = 64),
    source_excerpt  TEXT,
    UNIQUE (event_id, work_id, local_scene_uid, start_line)
) STRICT;

CREATE TABLE claim_predicates (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT
) STRICT;

CREATE TABLE universe_claims (
    id                  INTEGER PRIMARY KEY,
    subject_entity_id   INTEGER NOT NULL REFERENCES universe_entities(id) ON DELETE CASCADE,
    predicate_id        INTEGER NOT NULL REFERENCES claim_predicates(id),
    object_entity_id    INTEGER REFERENCES universe_entities(id) ON DELETE CASCADE,
    object_value_json   TEXT CHECK (object_value_json IS NULL OR json_valid(object_value_json)),
    continuity_id       INTEGER REFERENCES continuity_branches(id),
    canon_level_id      INTEGER REFERENCES canon_levels(id),
    confidence          REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    CHECK ((object_entity_id IS NOT NULL) <> (object_value_json IS NOT NULL))
) STRICT;

CREATE TABLE claim_sources (
    claim_id        INTEGER NOT NULL REFERENCES universe_claims(id) ON DELETE CASCADE,
    work_id         INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    local_scene_uid TEXT NOT NULL,
    start_line      INTEGER CHECK (start_line IS NULL OR start_line >= 1),
    end_line        INTEGER CHECK (
        end_line IS NULL OR (start_line IS NOT NULL AND end_line >= start_line)
    ),
    source_sha256   TEXT CHECK (source_sha256 IS NULL OR length(source_sha256) = 64),
    source_excerpt  TEXT,
    extraction_method TEXT NOT NULL,
    PRIMARY KEY (claim_id, work_id, local_scene_uid)
) STRICT, WITHOUT ROWID;

CREATE INDEX idx_universe_claims_subject
    ON universe_claims(subject_entity_id, predicate_id);

CREATE TABLE claim_conflicts (
    first_claim_id  INTEGER NOT NULL REFERENCES universe_claims(id) ON DELETE CASCADE,
    second_claim_id INTEGER NOT NULL REFERENCES universe_claims(id) ON DELETE CASCADE,
    explanation     TEXT,
    status          TEXT NOT NULL DEFAULT 'open',
    CHECK (first_claim_id < second_claim_id),
    PRIMARY KEY (first_claim_id, second_claim_id)
) STRICT, WITHOUT ROWID;

INSERT INTO entity_types(code, label, description) VALUES
    ('character', 'Personagem', 'Pessoa ou agente compartilhado'),
    ('location', 'Local', 'Lugar compartilhado'),
    ('organization', 'Organização', 'Grupo, instituição ou facção'),
    ('object', 'Objeto', 'Item relevante entre obras'),
    ('concept', 'Conceito', 'Regra, poder ou conceito abstrato');

INSERT INTO mapping_kinds(code, label, description) VALUES
    ('same_identity', 'Mesma identidade', 'Representações da mesma entidade'),
    ('alias_identity', 'Identidade por alias', 'Nome distinto da mesma entidade'),
    ('adaptation_counterpart', 'Contraparte', 'Equivalente em outra continuidade'),
    ('uncertain', 'Incerto', 'Correspondência ainda não confirmada');

INSERT INTO canon_levels(code, label, authority_rank, description) VALUES
    ('working_canon', 'Cânone de trabalho', 10, 'Versão adotada pelo projeto'),
    ('published_primary', 'Publicado primário', 20, 'Texto publicado primário'),
    ('posthumous', 'Póstumo', 30, 'Material publicado postumamente'),
    ('manuscript', 'Manuscrito', 40, 'Rascunho ou manuscrito'),
    ('adaptation', 'Adaptação', 50, 'Continuidade de adaptação'),
    ('critical_interpretation', 'Interpretação crítica', 60, 'Leitura editorial ou crítica');

INSERT INTO continuity_branches(code, label, description, is_default) VALUES
    ('main', 'Continuidade principal', 'Continuidade padrão do universo', 1);

INSERT INTO relationship_types(code, label, is_symmetric, description) VALUES
    ('related_to', 'Relacionado a', 1, 'Relação genérica'),
    ('parent_of', 'Progenitor de', 0, 'Relação de ascendência'),
    ('member_of', 'Membro de', 0, 'Vínculo com grupo ou organização'),
    ('located_in', 'Localizado em', 0, 'Vínculo espacial'),
    ('possesses', 'Possui', 0, 'Posse de objeto'),
    ('opposes', 'Opõe-se a', 1, 'Conflito ou oposição');

INSERT INTO event_precedence_types(code, label) VALUES
    ('before', 'Antes de'),
    ('immediately_before', 'Imediatamente antes de'),
    ('overlaps', 'Sobrepõe-se a');
"""


UNIVERSE_MIGRATION_002 = r"""
CREATE TABLE hash_algorithms (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    digest_size INTEGER NOT NULL CHECK (digest_size > 0),
    description TEXT
) STRICT;

CREATE TABLE merkle_root_kinds (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT NOT NULL
) STRICT;

CREATE TABLE work_merkle_roots (
    work_id         INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    root_kind_id    INTEGER NOT NULL REFERENCES merkle_root_kinds(id),
    algorithm_id    INTEGER NOT NULL REFERENCES hash_algorithms(id),
    root_hash       TEXT NOT NULL CHECK (length(root_hash) = 64),
    imported_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (work_id, root_kind_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE universe_merkle_roots (
    universe_id     INTEGER NOT NULL REFERENCES universes(id) ON DELETE CASCADE,
    root_kind_id    INTEGER NOT NULL REFERENCES merkle_root_kinds(id),
    algorithm_id    INTEGER NOT NULL REFERENCES hash_algorithms(id),
    root_hash       TEXT NOT NULL CHECK (length(root_hash) = 64),
    computed_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (universe_id, root_kind_id)
) STRICT, WITHOUT ROWID;

CREATE INDEX idx_universe_work_merkle_hash
    ON work_merkle_roots(root_hash, root_kind_id);

INSERT INTO hash_algorithms(code, label, digest_size, description) VALUES
    ('sha256-domain-v1', 'SHA-256 com separação de domínio v1', 32,
     'SHA-256 sobre partes prefixadas por tamanho e domínio editorial');

INSERT INTO merkle_root_kinds(code, label, description) VALUES
    ('content', 'Conteúdo', 'Agregação dos roots textuais das obras'),
    ('structure', 'Estrutura', 'Obras, identidades e ordem editorial'),
    ('materialization', 'Materialização', 'Configurações derivadas das obras'),
    ('knowledge', 'Conhecimento', 'Entidades, relações, claims e cronologia');
"""


UNIVERSE_MIGRATION_003 = r"""
-- Proveniência idempotente dos fatos derivados de cada banco por livro.
ALTER TABLE cross_work_relationships ADD COLUMN source_work_id INTEGER REFERENCES works(id) ON DELETE CASCADE;
ALTER TABLE cross_work_relationships ADD COLUMN source_local_relationship_id INTEGER;
CREATE UNIQUE INDEX idx_synced_relationship_identity
    ON cross_work_relationships(source_work_id, source_local_relationship_id)
    WHERE source_work_id IS NOT NULL AND source_local_relationship_id IS NOT NULL;

ALTER TABLE universe_claims ADD COLUMN source_work_id INTEGER REFERENCES works(id) ON DELETE CASCADE;
ALTER TABLE universe_claims ADD COLUMN source_local_claim_id INTEGER;
CREATE UNIQUE INDEX idx_synced_claim_identity
    ON universe_claims(source_work_id, source_local_claim_id)
    WHERE source_work_id IS NOT NULL AND source_local_claim_id IS NOT NULL;

CREATE TABLE universe_sync_runs (
    id              INTEGER PRIMARY KEY,
    work_id         INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    source_content_root TEXT NOT NULL CHECK (length(source_content_root) = 64),
    entities_count  INTEGER NOT NULL DEFAULT 0,
    relationships_count INTEGER NOT NULL DEFAULT 0,
    claims_count    INTEGER NOT NULL DEFAULT 0,
    completed_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;
"""


UNIVERSE_MIGRATIONS: Final[tuple[tuple[int, str, str], ...]] = (
    (1, "schema inicial de universo compartilhado", UNIVERSE_MIGRATION_001),
    (2, "Merkle roots agregados por obra e universo", UNIVERSE_MIGRATION_002),
    (3, "sync idempotente de relações e claims por obra", UNIVERSE_MIGRATION_003),
)


def universe_database_path(universe_dir: str | Path) -> Path:
    return Path(universe_dir).expanduser().resolve() / UNIVERSE_DB_FILENAME


def migrate_universe(connection: sqlite3.Connection) -> int:
    current = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if current > LATEST_UNIVERSE_SCHEMA_VERSION:
        raise SchemaVersionError(
            f"schema de universo v{current} é mais novo que o suportado "
            f"(v{LATEST_UNIVERSE_SCHEMA_VERSION})"
        )
    for version, description, sql in UNIVERSE_MIGRATIONS:
        if version <= current:
            continue
        escaped_description = description.replace("'", "''")
        try:
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                + sql
                + "\nINSERT INTO schema_migrations(version, description) "
                f"VALUES ({version}, '{escaped_description}');\n"
                f"PRAGMA user_version = {version};\nCOMMIT;"
            )
        except sqlite3.Error:
            if connection.in_transaction:
                connection.rollback()
            raise
        current = version
    return current


def initialize_universe_database(
    universe_dir: str | Path,
    *,
    universe_uid: str,
    slug: str | None = None,
    name: str | None = None,
    description: str | None = None,
    settings: DatabaseSettings | None = None,
) -> Path:
    """Cria/migra o índice derivado de um universo editorial."""

    root = Path(universe_dir).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"pasta do universo não encontrada: {root}")
    if len(universe_uid.strip()) < 8:
        raise ValueError("universe_uid deve ser uma identidade estável")

    db_path = universe_database_path(root)
    connection = connect(db_path, settings=settings)
    try:
        migrate_universe(connection)
        effective_slug = slug or root.name
        with transaction(connection):
            connection.execute(
                """
                INSERT INTO universes(
                    id, universe_uid, slug, name, canonical_root, description
                ) VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    universe_uid = excluded.universe_uid,
                    slug = excluded.slug,
                    name = excluded.name,
                    canonical_root = excluded.canonical_root,
                    description = COALESCE(excluded.description, universes.description),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    universe_uid,
                    effective_slug,
                    name or effective_slug,
                    str(root),
                    description,
                ),
            )
        connection.execute("PRAGMA optimize")
    finally:
        connection.close()
    return db_path


def _merkle_ids(connection: sqlite3.Connection) -> tuple[int, dict[str, int]]:
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


def import_book_merkle_roots(
    universe_connection: sqlite3.Connection,
    *,
    work_uid: str,
    book_db_path: str | Path,
) -> MerkleRootSet:
    """Importa somente roots de uma obra; nenhum texto cru cruza bancos."""

    work = universe_connection.execute(
        "SELECT id FROM works WHERE work_uid = ?", (work_uid,)
    ).fetchone()
    if work is None:
        raise KeyError(f"obra não registrada no universo: {work_uid}")
    book_connection = connect(book_db_path, read_only=True)
    try:
        rows = book_connection.execute(
            """SELECT kind.code, root.root_hash
               FROM work_merkle_roots AS root
               JOIN merkle_root_kinds AS kind ON kind.id = root.root_kind_id
               JOIN works AS work ON work.id = root.work_id
               WHERE work.work_uid = ?""",
            (work_uid,),
        ).fetchall()
    finally:
        book_connection.close()
    roots = {row["code"]: row["root_hash"] for row in rows}
    required = {"content", "structure", "materialization", "knowledge"}
    missing = sorted(required - roots.keys())
    if missing:
        raise RuntimeError(
            f"obra {work_uid} não possui roots Merkle: {', '.join(missing)}"
        )

    algorithm_id, kinds = _merkle_ids(universe_connection)
    for code in sorted(required):
        universe_connection.execute(
            """
            INSERT INTO work_merkle_roots(
                work_id, root_kind_id, algorithm_id, root_hash
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(work_id, root_kind_id) DO UPDATE SET
                algorithm_id = excluded.algorithm_id,
                root_hash = excluded.root_hash,
                imported_at = CASE WHEN root_hash <> excluded.root_hash
                                   THEN CURRENT_TIMESTAMP ELSE imported_at END
            """,
            (work["id"], kinds[code], algorithm_id, roots[code]),
        )
    return MerkleRootSet(
        roots["content"],
        roots["structure"],
        roots["materialization"],
        roots["knowledge"],
    )


def _universe_knowledge_leaves(connection: sqlite3.Connection) -> list[str]:
    queries = (
        (
            "universe-entity",
            """SELECT entity.entity_uid, type.code, entity.canonical_name,
                      entity.description
               FROM universe_entities AS entity
               JOIN entity_types AS type ON type.id = entity.entity_type_id""",
        ),
        (
            "universe-alias",
            """SELECT entity.entity_uid, alias.alias, alias.language, alias.notes
               FROM universe_entity_aliases AS alias
               JOIN universe_entities AS entity ON entity.id = alias.entity_id""",
        ),
        (
            "universe-mapping",
            """SELECT entity.entity_uid, work.work_uid, mapping.local_entity_uid,
                      kind.code, mapping.confidence, mapping.evidence_json
               FROM work_entity_mappings AS mapping
               JOIN universe_entities AS entity ON entity.id = mapping.universe_entity_id
               JOIN works AS work ON work.id = mapping.work_id
               JOIN mapping_kinds AS kind ON kind.id = mapping.mapping_kind_id""",
        ),
        (
            "universe-relationship",
            """SELECT source.entity_uid, target.entity_uid, type.code,
                      continuity.code, canon.code, relationship.valid_from_event_uid,
                      relationship.valid_to_event_uid, relationship.confidence,
                      relationship.notes
               FROM cross_work_relationships AS relationship
               JOIN universe_entities AS source ON source.id = relationship.source_entity_id
               JOIN universe_entities AS target ON target.id = relationship.target_entity_id
               JOIN relationship_types AS type ON type.id = relationship.relationship_type_id
               LEFT JOIN continuity_branches AS continuity ON continuity.id = relationship.continuity_id
               LEFT JOIN canon_levels AS canon ON canon.id = relationship.canon_level_id""",
        ),
        (
            "universe-relationship-source",
            """SELECT source.entity_uid, target.entity_uid, type.code,
                      work.work_uid, provenance.local_scene_uid,
                      provenance.start_line, provenance.end_line,
                      provenance.source_sha256, provenance.source_excerpt,
                      provenance.extraction_method
               FROM relationship_sources AS provenance
               JOIN cross_work_relationships AS relationship
                    ON relationship.id = provenance.relationship_id
               JOIN universe_entities AS source ON source.id = relationship.source_entity_id
               JOIN universe_entities AS target ON target.id = relationship.target_entity_id
               JOIN relationship_types AS type ON type.id = relationship.relationship_type_id
               JOIN works AS work ON work.id = provenance.work_id""",
        ),
        (
            "universe-event",
            """SELECT event.event_uid, continuity.code, calendar.code, event.label,
                      event.summary, event.chronology_sort_key, event.date_label,
                      event.date_precision
               FROM timeline_events AS event
               LEFT JOIN continuity_branches AS continuity ON continuity.id = event.continuity_id
               LEFT JOIN calendars AS calendar ON calendar.id = event.calendar_id""",
        ),
        (
            "universe-event-participant",
            """SELECT event.event_uid, entity.entity_uid, participant.role
               FROM event_participants AS participant
               JOIN timeline_events AS event ON event.id = participant.event_id
               JOIN universe_entities AS entity ON entity.id = participant.entity_id""",
        ),
        (
            "universe-event-location",
            """SELECT event.event_uid, entity.entity_uid
               FROM event_locations AS location
               JOIN timeline_events AS event ON event.id = location.event_id
               JOIN universe_entities AS entity ON entity.id = location.entity_id""",
        ),
        (
            "universe-event-precedence",
            """SELECT earlier.event_uid, later.event_uid, type.code,
                      precedence.confidence
               FROM event_precedence AS precedence
               JOIN timeline_events AS earlier ON earlier.id = precedence.earlier_event_id
               JOIN timeline_events AS later ON later.id = precedence.later_event_id
               JOIN event_precedence_types AS type ON type.id = precedence.precedence_type_id""",
        ),
        (
            "universe-event-source",
            """SELECT event.event_uid, work.work_uid, source.local_scene_uid,
                      source.start_line, source.end_line, source.source_sha256,
                      source.source_excerpt
               FROM event_sources AS source
               JOIN timeline_events AS event ON event.id = source.event_id
               JOIN works AS work ON work.id = source.work_id""",
        ),
        (
            "universe-claim",
            """SELECT subject.entity_uid, predicate.code, object.entity_uid,
                      claim.object_value_json, continuity.code, canon.code,
                      claim.confidence
               FROM universe_claims AS claim
               JOIN universe_entities AS subject ON subject.id = claim.subject_entity_id
               JOIN claim_predicates AS predicate ON predicate.id = claim.predicate_id
               LEFT JOIN universe_entities AS object ON object.id = claim.object_entity_id
               LEFT JOIN continuity_branches AS continuity ON continuity.id = claim.continuity_id
               LEFT JOIN canon_levels AS canon ON canon.id = claim.canon_level_id""",
        ),
        (
            "universe-claim-source",
            """SELECT subject.entity_uid, predicate.code, work.work_uid,
                      source.local_scene_uid, source.start_line, source.end_line,
                      source.source_sha256, source.source_excerpt,
                      source.extraction_method
               FROM claim_sources AS source
               JOIN universe_claims AS claim ON claim.id = source.claim_id
               JOIN universe_entities AS subject ON subject.id = claim.subject_entity_id
               JOIN claim_predicates AS predicate ON predicate.id = claim.predicate_id
               JOIN works AS work ON work.id = source.work_id""",
        ),
        (
            "universe-claim-conflict",
            """SELECT first_subject.entity_uid, first_predicate.code,
                      first_object.entity_uid, first.object_value_json,
                      second_subject.entity_uid, second_predicate.code,
                      second_object.entity_uid, second.object_value_json,
                      conflict.explanation, conflict.status
               FROM claim_conflicts AS conflict
               JOIN universe_claims AS first ON first.id = conflict.first_claim_id
               JOIN universe_claims AS second ON second.id = conflict.second_claim_id
               JOIN universe_entities AS first_subject
                    ON first_subject.id = first.subject_entity_id
               JOIN claim_predicates AS first_predicate
                    ON first_predicate.id = first.predicate_id
               LEFT JOIN universe_entities AS first_object
                    ON first_object.id = first.object_entity_id
               JOIN universe_entities AS second_subject
                    ON second_subject.id = second.subject_entity_id
               JOIN claim_predicates AS second_predicate
                    ON second_predicate.id = second.predicate_id
               LEFT JOIN universe_entities AS second_object
                    ON second_object.id = second.object_entity_id""",
        ),
    )
    leaves: list[str] = []
    for domain, query in queries:
        for row in connection.execute(query):
            values = list(row)
            if domain == "universe-mapping":
                values[5] = canonicalize_json_text(values[5])
            elif domain == "universe-claim":
                values[3] = canonicalize_json_text(values[3])
            elif domain == "universe-claim-conflict":
                values[3] = canonicalize_json_text(values[3])
                values[7] = canonicalize_json_text(values[7])
            leaves.append(hash_node(domain, *values))
    return sorted(leaves)


def refresh_universe_merkle_roots(
    connection: sqlite3.Connection,
) -> MerkleRootSet:
    """Agrega roots importados e o grafo de conhecimento compartilhado."""

    algorithm_id, kinds = _merkle_ids(connection)
    universe = connection.execute(
        "SELECT universe_uid, slug, name FROM universes WHERE id = 1"
    ).fetchone()
    if universe is None:
        raise RuntimeError("universo ainda não inicializado")
    rows = connection.execute(
        """SELECT work.work_uid, work.title, kind.code, root.root_hash
           FROM works AS work
           JOIN work_merkle_roots AS root ON root.work_id = work.id
           JOIN merkle_root_kinds AS kind ON kind.id = root.root_kind_id
           ORDER BY work.work_uid, kind.code"""
    ).fetchall()
    by_kind: dict[str, list[str]] = {
        "content": [],
        "structure": [],
        "materialization": [],
        "knowledge": [],
    }
    for row in rows:
        if row["code"] in by_kind:
            by_kind[row["code"]].extend([row["work_uid"], row["root_hash"]])

    content_root = hash_node("universe-content", *by_kind["content"])
    structure_root = hash_node(
        "universe-structure",
        universe["universe_uid"],
        universe["name"],
        *by_kind["structure"],
    )
    materialization_root = hash_node(
        "universe-materialization", *by_kind["materialization"]
    )
    knowledge_root = hash_node(
        "universe-knowledge",
        *by_kind["knowledge"],
        *_universe_knowledge_leaves(connection),
    )
    for code, root in (
        ("content", content_root),
        ("structure", structure_root),
        ("materialization", materialization_root),
        ("knowledge", knowledge_root),
    ):
        connection.execute(
            """
            INSERT INTO universe_merkle_roots(
                universe_id, root_kind_id, algorithm_id, root_hash
            ) VALUES (1, ?, ?, ?)
            ON CONFLICT(universe_id, root_kind_id) DO UPDATE SET
                algorithm_id = excluded.algorithm_id,
                root_hash = excluded.root_hash,
                computed_at = CASE WHEN root_hash <> excluded.root_hash
                                   THEN CURRENT_TIMESTAMP ELSE computed_at END
            """,
            (kinds[code], algorithm_id, root),
        )
    return MerkleRootSet(
        content_root, structure_root, materialization_root, knowledge_root
    )
