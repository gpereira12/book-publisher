"""Motor SQLite derivado e isolado por livro.

Os arquivos Markdown/YAML continuam sendo a fonte canônica. Este módulo cria e
mantém somente o índice reconstruível ``inputs/<livro>/.book_index.db``.

O módulo usa apenas a biblioteca padrão. FTS5 faz parte do schema principal;
sqlite-vec é habilitado explicitamente, quando a extensão estiver instalada.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final


DB_FILENAME: Final = ".book_index.db"
LATEST_SCHEMA_VERSION: Final = 7
DEFAULT_MMAP_SIZE: Final = 256 * 1024 * 1024
DEFAULT_BUSY_TIMEOUT_MS: Final = 5_000


class DatabaseEngineError(RuntimeError):
    """Erro de configuração ou migração do índice derivado."""


class SchemaVersionError(DatabaseEngineError):
    """O banco foi criado por uma versão mais nova da aplicação."""


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Ajustes locais de conexão; não são persistidos como configuração editorial."""

    mmap_size: int = DEFAULT_MMAP_SIZE
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS
    wal_autocheckpoint_pages: int = 1_000

    def __post_init__(self) -> None:
        if self.mmap_size < 0:
            raise ValueError("mmap_size não pode ser negativo")
        if self.busy_timeout_ms < 0:
            raise ValueError("busy_timeout_ms não pode ser negativo")
        if self.wal_autocheckpoint_pages <= 0:
            raise ValueError("wal_autocheckpoint_pages deve ser positivo")


MIGRATION_001 = r"""
CREATE TABLE schema_migrations (
    version        INTEGER PRIMARY KEY,
    description    TEXT NOT NULL,
    applied_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE books (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    slug            TEXT NOT NULL UNIQUE,
    title           TEXT,
    canonical_root  TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE documents (
    id              INTEGER PRIMARY KEY,
    book_id         INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL,
    relative_path   TEXT NOT NULL,
    content_sha256  TEXT CHECK (content_sha256 IS NULL OR length(content_sha256) = 64),
    byte_size       INTEGER CHECK (byte_size IS NULL OR byte_size >= 0),
    modified_ns     INTEGER CHECK (modified_ns IS NULL OR modified_ns >= 0),
    indexed_at      TEXT,
    UNIQUE (book_id, relative_path)
) STRICT;

CREATE TABLE chapters (
    id              INTEGER PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal         INTEGER NOT NULL CHECK (ordinal >= 0),
    stable_key      TEXT NOT NULL,
    title           TEXT,
    start_line      INTEGER NOT NULL CHECK (start_line >= 1),
    end_line        INTEGER NOT NULL CHECK (end_line >= start_line),
    UNIQUE (document_id, stable_key),
    UNIQUE (document_id, ordinal)
) STRICT;

CREATE TABLE scenes (
    id              INTEGER PRIMARY KEY,
    chapter_id      INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    ordinal         INTEGER NOT NULL CHECK (ordinal >= 0),
    stable_key      TEXT NOT NULL,
    scene_title     TEXT,
    start_line      INTEGER NOT NULL CHECK (start_line >= 1),
    end_line        INTEGER NOT NULL CHECK (end_line >= start_line),
    content         TEXT NOT NULL,
    content_sha256  TEXT NOT NULL CHECK (length(content_sha256) = 64),
    token_count     INTEGER CHECK (token_count IS NULL OR token_count >= 0),
    indexed_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (chapter_id, stable_key),
    UNIQUE (chapter_id, ordinal)
) STRICT;

CREATE INDEX idx_chapters_document_lines
    ON chapters(document_id, start_line, end_line);
CREATE INDEX idx_scenes_chapter_lines
    ON scenes(chapter_id, start_line, end_line);
CREATE INDEX idx_scenes_content_hash ON scenes(content_sha256);

CREATE VIRTUAL TABLE scene_fts USING fts5(
    scene_title,
    content,
    content = 'scenes',
    content_rowid = 'id',
    tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TRIGGER scenes_fts_after_insert AFTER INSERT ON scenes BEGIN
    INSERT INTO scene_fts(rowid, scene_title, content)
    VALUES (new.id, new.scene_title, new.content);
END;
CREATE TRIGGER scenes_fts_after_delete AFTER DELETE ON scenes BEGIN
    INSERT INTO scene_fts(scene_fts, rowid, scene_title, content)
    VALUES ('delete', old.id, old.scene_title, old.content);
END;
CREATE TRIGGER scenes_fts_after_update AFTER UPDATE OF scene_title, content ON scenes BEGIN
    INSERT INTO scene_fts(scene_fts, rowid, scene_title, content)
    VALUES ('delete', old.id, old.scene_title, old.content);
    INSERT INTO scene_fts(rowid, scene_title, content)
    VALUES (new.id, new.scene_title, new.content);
END;

CREATE TABLE entity_types (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT
) STRICT;

CREATE TABLE entities (
    id              INTEGER PRIMARY KEY,
    book_id         INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    entity_type_id  INTEGER NOT NULL REFERENCES entity_types(id),
    canonical_name  TEXT NOT NULL COLLATE NOCASE,
    description     TEXT,
    first_scene_id  INTEGER REFERENCES scenes(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (book_id, entity_type_id, canonical_name)
) STRICT;

CREATE TABLE entity_aliases (
    id          INTEGER PRIMARY KEY,
    entity_id   INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    alias       TEXT NOT NULL COLLATE NOCASE,
    UNIQUE (entity_id, alias)
) STRICT;

CREATE TABLE entity_mentions (
    id              INTEGER PRIMARY KEY,
    entity_id       INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    scene_id        INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    start_offset    INTEGER CHECK (start_offset IS NULL OR start_offset >= 0),
    end_offset      INTEGER CHECK (end_offset IS NULL OR end_offset >= start_offset),
    surface_form    TEXT,
    confidence      REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    UNIQUE (entity_id, scene_id, start_offset, end_offset)
) STRICT;

CREATE INDEX idx_entity_mentions_scene ON entity_mentions(scene_id);

CREATE TABLE relationship_types (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    is_symmetric    INTEGER NOT NULL DEFAULT 0 CHECK (is_symmetric IN (0, 1)),
    description     TEXT
) STRICT;

CREATE TABLE entity_relationships (
    id                      INTEGER PRIMARY KEY,
    source_entity_id        INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id        INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type_id    INTEGER NOT NULL REFERENCES relationship_types(id),
    valid_from_scene_id     INTEGER REFERENCES scenes(id) ON DELETE SET NULL,
    valid_to_scene_id       INTEGER REFERENCES scenes(id) ON DELETE SET NULL,
    notes                   TEXT,
    CHECK (source_entity_id <> target_entity_id),
    UNIQUE (source_entity_id, target_entity_id, relationship_type_id, valid_from_scene_id)
) STRICT;

CREATE TABLE state_attributes (
    id              INTEGER PRIMARY KEY,
    entity_type_id  INTEGER REFERENCES entity_types(id),
    code            TEXT NOT NULL,
    label           TEXT NOT NULL,
    value_kind      TEXT NOT NULL CHECK (value_kind IN ('text', 'number', 'boolean', 'json')),
    description     TEXT,
    UNIQUE (entity_type_id, code)
) STRICT;

CREATE TABLE entity_state_events (
    id              INTEGER PRIMARY KEY,
    entity_id       INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    scene_id        INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    event_ordinal   INTEGER NOT NULL DEFAULT 0 CHECK (event_ordinal >= 0),
    summary         TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (entity_id, scene_id, event_ordinal)
) STRICT;

CREATE TABLE entity_state_deltas (
    event_id        INTEGER NOT NULL REFERENCES entity_state_events(id) ON DELETE CASCADE,
    attribute_id    INTEGER NOT NULL REFERENCES state_attributes(id),
    old_value_json  TEXT CHECK (old_value_json IS NULL OR json_valid(old_value_json)),
    new_value_json  TEXT NOT NULL CHECK (json_valid(new_value_json)),
    PRIMARY KEY (event_id, attribute_id)
) STRICT, WITHOUT ROWID;

CREATE INDEX idx_state_events_timeline
    ON entity_state_events(entity_id, scene_id, event_ordinal);

CREATE TABLE edit_layers (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT
) STRICT;

CREATE TABLE severities (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    rank        INTEGER NOT NULL UNIQUE CHECK (rank >= 0)
) STRICT;

CREATE TABLE review_findings (
    id              INTEGER PRIMARY KEY,
    scene_id        INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    edit_layer_id   INTEGER NOT NULL REFERENCES edit_layers(id),
    severity_id     INTEGER NOT NULL REFERENCES severities(id),
    rule_code       TEXT NOT NULL,
    message         TEXT NOT NULL,
    suggestion      TEXT,
    start_offset    INTEGER CHECK (start_offset IS NULL OR start_offset >= 0),
    end_offset      INTEGER CHECK (end_offset IS NULL OR end_offset >= start_offset),
    confidence      REAL CHECK (confidence IS NULL OR confidence BETWEEN 0.0 AND 1.0),
    status          TEXT NOT NULL DEFAULT 'open',
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE scene_revisions (
    id                  INTEGER PRIMARY KEY,
    scene_id            INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    parent_revision_id  INTEGER REFERENCES scene_revisions(id) ON DELETE SET NULL,
    base_sha256         TEXT NOT NULL CHECK (length(base_sha256) = 64),
    result_sha256       TEXT NOT NULL CHECK (length(result_sha256) = 64),
    patch_text          TEXT NOT NULL,
    is_milestone        INTEGER NOT NULL DEFAULT 0 CHECK (is_milestone IN (0, 1)),
    author              TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE INDEX idx_scene_revisions_history
    ON scene_revisions(scene_id, created_at);

CREATE TABLE narrative_frameworks (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL,
    name            TEXT NOT NULL,
    version         TEXT NOT NULL,
    description     TEXT NOT NULL,
    writing_guide   TEXT NOT NULL,
    audit_checklist_json TEXT NOT NULL CHECK (json_valid(audit_checklist_json)),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    UNIQUE (code, version)
) STRICT;

CREATE TABLE framework_beats (
    id                  INTEGER PRIMARY KEY,
    framework_id        INTEGER NOT NULL REFERENCES narrative_frameworks(id) ON DELETE CASCADE,
    ordinal             INTEGER NOT NULL CHECK (ordinal >= 0),
    code                TEXT NOT NULL,
    name                TEXT NOT NULL,
    description         TEXT NOT NULL,
    writing_guide       TEXT NOT NULL,
    audit_checklist_json TEXT NOT NULL CHECK (json_valid(audit_checklist_json)),
    target_start_pct    REAL CHECK (target_start_pct IS NULL OR target_start_pct BETWEEN 0.0 AND 1.0),
    target_end_pct      REAL CHECK (target_end_pct IS NULL OR target_end_pct BETWEEN 0.0 AND 1.0),
    CHECK (target_start_pct IS NULL OR target_end_pct IS NULL OR target_start_pct <= target_end_pct),
    UNIQUE (framework_id, ordinal),
    UNIQUE (framework_id, code)
) STRICT;

CREATE TABLE scene_framework_beats (
    scene_id        INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    beat_id         INTEGER NOT NULL REFERENCES framework_beats(id) ON DELETE CASCADE,
    confidence      REAL CHECK (confidence IS NULL OR confidence BETWEEN 0.0 AND 1.0),
    notes           TEXT,
    PRIMARY KEY (scene_id, beat_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE embedding_models (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    model_name      TEXT NOT NULL,
    dimensions      INTEGER NOT NULL CHECK (dimensions > 0),
    distance_metric TEXT NOT NULL CHECK (distance_metric IN ('cosine', 'l2')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE scene_embedding_sources (
    scene_id        INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    model_id        INTEGER NOT NULL REFERENCES embedding_models(id) ON DELETE CASCADE,
    content_sha256  TEXT NOT NULL CHECK (length(content_sha256) = 64),
    embedded_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scene_id, model_id)
) STRICT, WITHOUT ROWID;

INSERT INTO entity_types(code, label, description) VALUES
    ('character', 'Personagem', 'Pessoa ou agente da narrativa'),
    ('location', 'Local', 'Lugar físico ou conceitual'),
    ('organization', 'Organização', 'Grupo, instituição ou facção'),
    ('object', 'Objeto', 'Item narrativamente relevante'),
    ('concept', 'Conceito', 'Regra, poder, tema ou conceito abstrato');

INSERT INTO edit_layers(code, label, description) VALUES
    ('developmental', 'Desenvolvimento', 'Estrutura, arco e intenção narrativa'),
    ('line', 'Edição de linha', 'Voz, ritmo, clareza e estilo'),
    ('copy', 'Copidesque', 'Gramática, consistência e precisão'),
    ('proof', 'Prova', 'Erros residuais e tipografia');

INSERT INTO severities(code, label, rank) VALUES
    ('info', 'Informação', 10),
    ('warning', 'Alerta', 20),
    ('error', 'Erro', 30),
    ('critical', 'Crítico', 40);
"""


MIGRATION_002 = r"""
-- Identidades opacas sobrevivem a renomeações e mudanças de capítulo.
ALTER TABLE scenes ADD COLUMN scene_uid TEXT;
UPDATE scenes SET scene_uid = lower(hex(randomblob(16))) WHERE scene_uid IS NULL;
CREATE UNIQUE INDEX idx_scenes_uid ON scenes(scene_uid);

CREATE TRIGGER scenes_require_uid_insert
BEFORE INSERT ON scenes
WHEN new.scene_uid IS NULL OR length(trim(new.scene_uid)) < 16
BEGIN
    SELECT RAISE(ABORT, 'scene_uid obrigatório (mínimo de 16 caracteres)');
END;

CREATE TRIGGER scenes_require_uid_update
BEFORE UPDATE OF scene_uid ON scenes
WHEN new.scene_uid IS NULL OR length(trim(new.scene_uid)) < 16
BEGIN
    SELECT RAISE(ABORT, 'scene_uid obrigatório (mínimo de 16 caracteres)');
END;

ALTER TABLE entities ADD COLUMN entity_uid TEXT;
ALTER TABLE entities ADD COLUMN universe_entity_uid TEXT;
UPDATE entities SET entity_uid = lower(hex(randomblob(16))) WHERE entity_uid IS NULL;
CREATE UNIQUE INDEX idx_entities_uid ON entities(entity_uid);
CREATE INDEX idx_entities_universe_uid ON entities(universe_entity_uid);

CREATE TRIGGER entities_require_uid_insert
BEFORE INSERT ON entities
WHEN new.entity_uid IS NULL OR length(trim(new.entity_uid)) < 16
BEGIN
    SELECT RAISE(ABORT, 'entity_uid obrigatório (mínimo de 16 caracteres)');
END;

CREATE TRIGGER entities_require_uid_update
BEFORE UPDATE OF entity_uid ON entities
WHEN new.entity_uid IS NULL OR length(trim(new.entity_uid)) < 16
BEGIN
    SELECT RAISE(ABORT, 'entity_uid obrigatório (mínimo de 16 caracteres)');
END;

-- Obra intelectual, edição e volume deixam de ser confundidos com arquivo.
CREATE TABLE works (
    id              INTEGER PRIMARY KEY,
    work_uid        TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    sort_title      TEXT,
    original_language TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE editions (
    id                  INTEGER PRIMARY KEY,
    work_id             INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    edition_uid         TEXT NOT NULL UNIQUE,
    label               TEXT NOT NULL,
    language            TEXT,
    publication_year    INTEGER CHECK (publication_year IS NULL OR publication_year > 0),
    is_working_edition  INTEGER NOT NULL DEFAULT 0 CHECK (is_working_edition IN (0, 1)),
    UNIQUE (work_id, label)
) STRICT;

CREATE TABLE volumes (
    id              INTEGER PRIMARY KEY,
    edition_id      INTEGER NOT NULL REFERENCES editions(id) ON DELETE CASCADE,
    volume_uid      TEXT NOT NULL UNIQUE,
    ordinal         INTEGER NOT NULL CHECK (ordinal >= 0),
    title           TEXT,
    UNIQUE (edition_id, ordinal)
) STRICT;

ALTER TABLE documents ADD COLUMN edition_id INTEGER REFERENCES editions(id) ON DELETE SET NULL;
ALTER TABLE documents ADD COLUMN volume_id INTEGER REFERENCES volumes(id) ON DELETE SET NULL;

-- Passagem é unidade de recuperação; cena continua sendo unidade editorial.
CREATE TABLE passages (
    id              INTEGER PRIMARY KEY,
    scene_id        INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    ordinal         INTEGER NOT NULL CHECK (ordinal >= 0),
    start_offset    INTEGER NOT NULL CHECK (start_offset >= 0),
    end_offset      INTEGER NOT NULL CHECK (end_offset > start_offset),
    start_line      INTEGER NOT NULL CHECK (start_line >= 1),
    end_line        INTEGER NOT NULL CHECK (end_line >= start_line),
    content         TEXT NOT NULL,
    content_sha256  TEXT NOT NULL CHECK (length(content_sha256) = 64),
    token_count     INTEGER CHECK (token_count IS NULL OR token_count >= 0),
    indexed_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (scene_id, ordinal),
    UNIQUE (scene_id, start_offset, end_offset)
) STRICT;

CREATE INDEX idx_passages_scene_offsets ON passages(scene_id, start_offset, end_offset);
CREATE INDEX idx_passages_content_hash ON passages(content_sha256);

CREATE VIRTUAL TABLE passage_fts USING fts5(
    content,
    content = 'passages',
    content_rowid = 'id',
    tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TRIGGER passages_fts_after_insert AFTER INSERT ON passages BEGIN
    INSERT INTO passage_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER passages_fts_after_delete AFTER DELETE ON passages BEGIN
    INSERT INTO passage_fts(passage_fts, rowid, content)
    VALUES ('delete', old.id, old.content);
END;
CREATE TRIGGER passages_fts_after_update AFTER UPDATE OF content ON passages BEGIN
    INSERT INTO passage_fts(passage_fts, rowid, content)
    VALUES ('delete', old.id, old.content);
    INSERT INTO passage_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TABLE passage_embedding_sources (
    passage_id      INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
    model_id        INTEGER NOT NULL REFERENCES embedding_models(id) ON DELETE CASCADE,
    content_sha256  TEXT NOT NULL CHECK (length(content_sha256) = 64),
    embedded_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (passage_id, model_id)
) STRICT, WITHOUT ROWID;

-- Grafo narrativo explícito dentro da obra.
CREATE TABLE scene_link_types (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    description     TEXT
) STRICT;

CREATE TABLE scene_links (
    id                  INTEGER PRIMARY KEY,
    source_scene_id     INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    target_scene_id     INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    scene_link_type_id  INTEGER NOT NULL REFERENCES scene_link_types(id),
    weight              REAL NOT NULL DEFAULT 1.0 CHECK (weight BETWEEN 0.0 AND 1.0),
    description         TEXT,
    provenance_kind     TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (source_scene_id <> target_scene_id),
    UNIQUE (source_scene_id, target_scene_id, scene_link_type_id)
) STRICT;

INSERT INTO scene_link_types(code, label, description) VALUES
    ('continues', 'Continua', 'Continua diretamente outra cena'),
    ('foreshadows', 'Antecipa', 'Planta ou antecipa um evento posterior'),
    ('resolves', 'Resolve', 'Resolve uma promessa, questão ou conflito'),
    ('parallels', 'Paralelo', 'Espelha tema, imagem ou estrutura'),
    ('contradicts', 'Contradiz', 'Apresenta informação incompatível'),
    ('flashback_to', 'Retorna a', 'Reencena ou recorda evento anterior'),
    ('same_event_as', 'Mesmo evento', 'Representa o mesmo evento por outro ponto de vista'),
    ('causes', 'Causa', 'Estabelece causalidade narrativa'),
    ('references', 'Referencia', 'Faz referência explícita'),
    ('retells', 'Reconta', 'Reconta material narrativo existente');

-- Continuidade, grau canônico e afirmações rastreáveis à cena.
CREATE TABLE canon_levels (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    authority_rank INTEGER NOT NULL UNIQUE CHECK (authority_rank >= 0),
    description TEXT
) STRICT;

CREATE TABLE continuity_branches (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT,
    is_default  INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1))
) STRICT;

CREATE UNIQUE INDEX idx_continuity_single_default
    ON continuity_branches(is_default) WHERE is_default = 1;

CREATE TABLE claim_predicates (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT
) STRICT;

CREATE TABLE entity_claims (
    id                  INTEGER PRIMARY KEY,
    subject_entity_id   INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    predicate_id        INTEGER NOT NULL REFERENCES claim_predicates(id),
    object_entity_id    INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    object_value_json   TEXT CHECK (object_value_json IS NULL OR json_valid(object_value_json)),
    asserted_scene_id   INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    canon_level_id      INTEGER REFERENCES canon_levels(id),
    continuity_id       INTEGER REFERENCES continuity_branches(id),
    confidence          REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    extraction_method   TEXT NOT NULL,
    source_excerpt      TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((object_entity_id IS NOT NULL) <> (object_value_json IS NOT NULL))
) STRICT;

CREATE INDEX idx_entity_claims_subject ON entity_claims(subject_entity_id, predicate_id);
CREATE INDEX idx_entity_claims_source ON entity_claims(asserted_scene_id);

INSERT INTO canon_levels(code, label, authority_rank, description) VALUES
    ('working_canon', 'Cânone de trabalho', 10, 'Versão canônica adotada pelo projeto'),
    ('published_primary', 'Publicado primário', 20, 'Texto publicado considerado primário'),
    ('posthumous', 'Póstumo', 30, 'Material publicado postumamente'),
    ('manuscript', 'Manuscrito', 40, 'Rascunho ou manuscrito de origem'),
    ('adaptation', 'Adaptação', 50, 'Continuidade de uma adaptação'),
    ('critical_interpretation', 'Interpretação crítica', 60, 'Leitura editorial ou crítica');

INSERT INTO continuity_branches(code, label, description, is_default) VALUES
    ('main', 'Continuidade principal', 'Continuidade padrão deste livro', 1);

-- Snapshots são aceleradores descartáveis sobre o event sourcing.
CREATE TABLE entity_state_snapshots (
    id                  INTEGER PRIMARY KEY,
    entity_id           INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    through_scene_id    INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    state_json          TEXT NOT NULL CHECK (json_valid(state_json)),
    source_event_count  INTEGER NOT NULL CHECK (source_event_count >= 0),
    generated_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (entity_id, through_scene_id)
) STRICT;
"""


MIGRATION_003 = r"""
-- Identidade de capítulo e controle explícito da materialização derivada.
ALTER TABLE chapters ADD COLUMN chapter_uid TEXT;
UPDATE chapters SET chapter_uid = lower(hex(randomblob(16))) WHERE chapter_uid IS NULL;
CREATE UNIQUE INDEX idx_chapters_uid ON chapters(chapter_uid);

CREATE TRIGGER chapters_require_uid_insert
BEFORE INSERT ON chapters
WHEN new.chapter_uid IS NULL OR length(trim(new.chapter_uid)) < 16
BEGIN
    SELECT RAISE(ABORT, 'chapter_uid obrigatório (mínimo de 16 caracteres)');
END;

CREATE TRIGGER chapters_require_uid_update
BEFORE UPDATE OF chapter_uid ON chapters
WHEN new.chapter_uid IS NULL OR length(trim(new.chapter_uid)) < 16
BEGIN
    SELECT RAISE(ABORT, 'chapter_uid obrigatório (mínimo de 16 caracteres)');
END;

ALTER TABLE documents ADD COLUMN parser_version TEXT;

CREATE TABLE derivation_kinds (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT
) STRICT;

CREATE TABLE derivation_statuses (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    is_queryable INTEGER NOT NULL CHECK (is_queryable IN (0, 1))
) STRICT;

CREATE TABLE scene_derivation_status (
    scene_id        INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    derivation_kind_id INTEGER NOT NULL REFERENCES derivation_kinds(id),
    status_id       INTEGER NOT NULL REFERENCES derivation_statuses(id),
    source_sha256   TEXT NOT NULL CHECK (length(source_sha256) = 64),
    generated_at    TEXT,
    details_json    TEXT CHECK (details_json IS NULL OR json_valid(details_json)),
    PRIMARY KEY (scene_id, derivation_kind_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE sync_runs (
    id                  INTEGER PRIMARY KEY,
    document_id         INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_sha256       TEXT NOT NULL CHECK (length(source_sha256) = 64),
    parser_version      TEXT NOT NULL,
    inserted_scenes     INTEGER NOT NULL DEFAULT 0 CHECK (inserted_scenes >= 0),
    updated_scenes      INTEGER NOT NULL DEFAULT 0 CHECK (updated_scenes >= 0),
    unchanged_scenes    INTEGER NOT NULL DEFAULT 0 CHECK (unchanged_scenes >= 0),
    deleted_scenes      INTEGER NOT NULL DEFAULT 0 CHECK (deleted_scenes >= 0),
    started_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at        TEXT,
    status              TEXT NOT NULL,
    error_message       TEXT
) STRICT;

CREATE INDEX idx_sync_runs_document ON sync_runs(document_id, started_at);

INSERT INTO derivation_kinds(code, label, description) VALUES
    ('passages', 'Passagens', 'Chunks determinísticos para recuperação'),
    ('embeddings', 'Embeddings', 'Vetores semânticos das passagens'),
    ('mentions', 'Menções', 'Menções de entidades extraídas'),
    ('entity_states', 'Estados', 'Eventos e deltas de estado'),
    ('review_findings', 'Achados', 'Resultados de auditoria editorial'),
    ('framework_beats', 'Beats', 'Mapeamento de estrutura narrativa');

INSERT INTO derivation_statuses(code, label, is_queryable) VALUES
    ('fresh', 'Atual', 1),
    ('stale', 'Desatualizado', 0),
    ('pending', 'Pendente', 0),
    ('failed', 'Falhou', 0);
"""


MIGRATION_004 = r"""
-- Merkle DAG editorial: conteúdo, estrutura, materialização e conhecimento
-- possuem roots independentes para evitar invalidações excessivas.
ALTER TABLE sync_runs ADD COLUMN content_merkle_root TEXT
    CHECK (content_merkle_root IS NULL OR length(content_merkle_root) = 64);
ALTER TABLE sync_runs ADD COLUMN structure_merkle_root TEXT
    CHECK (structure_merkle_root IS NULL OR length(structure_merkle_root) = 64);
ALTER TABLE sync_runs ADD COLUMN materialization_merkle_root TEXT
    CHECK (materialization_merkle_root IS NULL OR length(materialization_merkle_root) = 64);

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

CREATE TABLE passage_merkle_roots (
    passage_id      INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
    root_kind_id    INTEGER NOT NULL REFERENCES merkle_root_kinds(id),
    algorithm_id    INTEGER NOT NULL REFERENCES hash_algorithms(id),
    root_hash       TEXT NOT NULL CHECK (length(root_hash) = 64),
    source_sha256   TEXT NOT NULL CHECK (length(source_sha256) = 64),
    computed_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (passage_id, root_kind_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE scene_merkle_roots (
    scene_id        INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    root_kind_id    INTEGER NOT NULL REFERENCES merkle_root_kinds(id),
    algorithm_id    INTEGER NOT NULL REFERENCES hash_algorithms(id),
    root_hash       TEXT NOT NULL CHECK (length(root_hash) = 64),
    source_sha256   TEXT NOT NULL CHECK (length(source_sha256) = 64),
    config_hash     TEXT CHECK (config_hash IS NULL OR length(config_hash) = 64),
    computed_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scene_id, root_kind_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE chapter_merkle_roots (
    chapter_id      INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    root_kind_id    INTEGER NOT NULL REFERENCES merkle_root_kinds(id),
    algorithm_id    INTEGER NOT NULL REFERENCES hash_algorithms(id),
    root_hash       TEXT NOT NULL CHECK (length(root_hash) = 64),
    config_hash     TEXT CHECK (config_hash IS NULL OR length(config_hash) = 64),
    computed_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chapter_id, root_kind_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE document_merkle_roots (
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    root_kind_id    INTEGER NOT NULL REFERENCES merkle_root_kinds(id),
    algorithm_id    INTEGER NOT NULL REFERENCES hash_algorithms(id),
    root_hash       TEXT NOT NULL CHECK (length(root_hash) = 64),
    config_hash     TEXT CHECK (config_hash IS NULL OR length(config_hash) = 64),
    computed_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, root_kind_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE work_merkle_roots (
    work_id         INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    root_kind_id    INTEGER NOT NULL REFERENCES merkle_root_kinds(id),
    algorithm_id    INTEGER NOT NULL REFERENCES hash_algorithms(id),
    root_hash       TEXT NOT NULL CHECK (length(root_hash) = 64),
    config_hash     TEXT CHECK (config_hash IS NULL OR length(config_hash) = 64),
    computed_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (work_id, root_kind_id)
) STRICT, WITHOUT ROWID;

CREATE INDEX idx_document_merkle_hash
    ON document_merkle_roots(root_hash, root_kind_id);
CREATE INDEX idx_work_merkle_hash
    ON work_merkle_roots(root_hash, root_kind_id);

INSERT INTO hash_algorithms(code, label, digest_size, description) VALUES
    ('sha256-domain-v1', 'SHA-256 com separação de domínio v1', 32,
     'SHA-256 sobre partes prefixadas por tamanho e domínio editorial');

INSERT INTO merkle_root_kinds(code, label, description) VALUES
    ('content', 'Conteúdo', 'Texto sem posição, título ou configuração derivada'),
    ('structure', 'Estrutura', 'Identidades, títulos, ordem e composição'),
    ('materialization', 'Materialização', 'Conteúdo mais parser, chunks ou modelo'),
    ('knowledge', 'Conhecimento', 'Entidades, relações, claims, estados e cronologia');
"""


MIGRATION_005 = r"""
-- Seleção explícita da fonte editorial ativa e cache vetorial por conteúdo.
CREATE TABLE document_roles (
    id                  INTEGER PRIMARY KEY,
    code                TEXT NOT NULL UNIQUE,
    label               TEXT NOT NULL,
    context_priority    INTEGER NOT NULL UNIQUE CHECK (context_priority >= 0),
    is_manuscript       INTEGER NOT NULL CHECK (is_manuscript IN (0, 1)),
    description         TEXT
) STRICT;

CREATE TABLE edition_document_assignments (
    document_id         INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    edition_id          INTEGER NOT NULL REFERENCES editions(id) ON DELETE CASCADE,
    document_role_id    INTEGER NOT NULL REFERENCES document_roles(id),
    is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    assigned_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE UNIQUE INDEX idx_one_active_document_per_role
    ON edition_document_assignments(edition_id, document_role_id)
    WHERE is_active = 1;
CREATE INDEX idx_active_documents
    ON edition_document_assignments(edition_id, is_active, document_role_id);

ALTER TABLE embedding_models ADD COLUMN config_hash TEXT
    CHECK (config_hash IS NULL OR length(config_hash) = 64);

CREATE TABLE embedding_cache (
    model_id            INTEGER NOT NULL REFERENCES embedding_models(id) ON DELETE CASCADE,
    content_merkle_root TEXT NOT NULL CHECK (length(content_merkle_root) = 64),
    dimensions          INTEGER NOT NULL CHECK (dimensions > 0),
    embedding           BLOB NOT NULL,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (model_id, content_merkle_root)
) STRICT, WITHOUT ROWID;

CREATE TABLE vector_index_state (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    model_id            INTEGER NOT NULL REFERENCES embedding_models(id),
    dimensions          INTEGER NOT NULL CHECK (dimensions > 0),
    config_hash         TEXT NOT NULL CHECK (length(config_hash) = 64),
    rebuilt_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

INSERT INTO document_roles(
    code, label, context_priority, is_manuscript, description
) VALUES
    ('source_original', 'Original', 10, 1, 'Manuscrito original preservado'),
    ('working_revision', 'Revisão de trabalho', 20, 1, 'Revisão editorial corrente'),
    ('approved_manuscript', 'Manuscrito aprovado', 30, 1, 'Fonte aprovada para contexto'),
    ('translation', 'Tradução', 15, 1, 'Tradução ou localização'),
    ('appendix', 'Apêndice', 5, 0, 'Material complementar'),
    ('dossier', 'Dossiê', 6, 0, 'Worldbuilding e dados editoriais');

INSERT OR IGNORE INTO edition_document_assignments(
    document_id, edition_id, document_role_id, is_active
)
SELECT d.id, d.edition_id, role.id, 1
FROM documents AS d
JOIN document_roles AS role ON role.code = CASE
    WHEN lower(d.relative_path) LIKE '%revisado%' THEN 'working_revision'
    WHEN lower(d.relative_path) LIKE '%original%' THEN 'source_original'
    ELSE 'source_original'
END
WHERE d.edition_id IS NOT NULL;
"""


MIGRATION_006 = r"""
-- Confiabilidade operacional, genealogia e proveniência do conhecimento.
CREATE TABLE scene_tombstones (
    scene_uid           TEXT PRIMARY KEY,
    document_relative_path TEXT NOT NULL,
    chapter_uid         TEXT,
    stable_key          TEXT NOT NULL,
    scene_title         TEXT,
    last_content        TEXT NOT NULL,
    last_content_sha256 TEXT NOT NULL CHECK (length(last_content_sha256) = 64),
    removed_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    restored_at         TEXT,
    removal_reason      TEXT NOT NULL DEFAULT 'source_removed',
    metadata_json       TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json))
) STRICT;

CREATE TABLE archived_scene_revisions (
    original_revision_id INTEGER NOT NULL,
    parent_original_revision_id INTEGER,
    scene_uid            TEXT NOT NULL REFERENCES scene_tombstones(scene_uid) ON DELETE CASCADE,
    base_sha256          TEXT NOT NULL CHECK (length(base_sha256) = 64),
    result_sha256        TEXT NOT NULL CHECK (length(result_sha256) = 64),
    patch_text           TEXT NOT NULL,
    author               TEXT,
    created_at           TEXT NOT NULL,
    PRIMARY KEY (scene_uid, original_revision_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE scene_lineage_types (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT
) STRICT;

CREATE TABLE scene_lineage (
    parent_scene_uid TEXT NOT NULL,
    child_scene_uid  TEXT NOT NULL,
    lineage_type_id INTEGER NOT NULL REFERENCES scene_lineage_types(id),
    confidence      REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (parent_scene_uid <> child_scene_uid),
    PRIMARY KEY (parent_scene_uid, child_scene_uid, lineage_type_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE sync_attempts (
    id                  INTEGER PRIMARY KEY,
    document_relative_path TEXT NOT NULL,
    source_sha256       TEXT CHECK (source_sha256 IS NULL OR length(source_sha256) = 64),
    parser_version      TEXT,
    status              TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    started_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at        TEXT,
    error_type          TEXT,
    error_message       TEXT
) STRICT;

CREATE TABLE writer_leases (
    lease_name      TEXT PRIMARY KEY,
    owner_id        TEXT NOT NULL,
    acquired_at_epoch INTEGER NOT NULL,
    heartbeat_at_epoch INTEGER NOT NULL,
    expires_at_epoch INTEGER NOT NULL,
    CHECK (expires_at_epoch > acquired_at_epoch)
) STRICT, WITHOUT ROWID;

CREATE TABLE document_availability (
    document_id     INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    status          TEXT NOT NULL CHECK (status IN ('available', 'missing')),
    checked_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    missing_since   TEXT
) STRICT;

CREATE TABLE authority_sources (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    authority_rank  INTEGER NOT NULL UNIQUE CHECK (authority_rank >= 0),
    description     TEXT
) STRICT;

CREATE TABLE knowledge_ingestion_runs (
    id              INTEGER PRIMARY KEY,
    relative_path   TEXT NOT NULL,
    content_sha256  TEXT NOT NULL CHECK (length(content_sha256) = 64),
    status          TEXT NOT NULL CHECK (status IN ('completed', 'failed')),
    entities_count  INTEGER NOT NULL DEFAULT 0,
    claims_count    INTEGER NOT NULL DEFAULT 0,
    completed_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message   TEXT
) STRICT;

CREATE TABLE knowledge_source_claims (
    relative_path   TEXT NOT NULL,
    claim_id        INTEGER NOT NULL UNIQUE REFERENCES entity_claims(id) ON DELETE CASCADE,
    PRIMARY KEY (relative_path, claim_id)
) STRICT, WITHOUT ROWID;

ALTER TABLE entities ADD COLUMN authority_source_id INTEGER REFERENCES authority_sources(id);
ALTER TABLE entity_claims ADD COLUMN authority_source_id INTEGER REFERENCES authority_sources(id);
ALTER TABLE entity_aliases ADD COLUMN extraction_method TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE entity_aliases ADD COLUMN source_relative_path TEXT;
ALTER TABLE entity_mentions ADD COLUMN extraction_method TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE entity_mentions ADD COLUMN source_relative_path TEXT;
ALTER TABLE entity_relationships ADD COLUMN extraction_method TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE entity_relationships ADD COLUMN source_relative_path TEXT;
ALTER TABLE entity_state_events ADD COLUMN extraction_method TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE entity_state_events ADD COLUMN source_relative_path TEXT;

CREATE INDEX idx_aliases_knowledge_source
    ON entity_aliases(source_relative_path, extraction_method);
CREATE INDEX idx_mentions_knowledge_source
    ON entity_mentions(source_relative_path, extraction_method);
CREATE INDEX idx_relationships_knowledge_source
    ON entity_relationships(source_relative_path, extraction_method);
CREATE INDEX idx_state_events_knowledge_source
    ON entity_state_events(source_relative_path, extraction_method);

INSERT INTO scene_lineage_types(code, label, description) VALUES
    ('split_into', 'Dividida em', 'Cena ancestral dividida em cenas descendentes'),
    ('merged_into', 'Fundida em', 'Cena ancestral incorporada a outra cena'),
    ('derived_from', 'Derivada de', 'Cena editorial derivada de outra identidade');

INSERT INTO authority_sources(code, label, authority_rank, description) VALUES
    ('approved_canon', 'Cânone aprovado', 100, 'Conhecimento explicitamente aprovado'),
    ('editorial_dossier', 'Dossiê editorial', 80, 'YAML canônico mantido pela equipe'),
    ('manuscript_explicit', 'Manuscrito explícito', 60, 'Extração determinística do texto'),
    ('model_suggestion', 'Sugestão de modelo', 20, 'Inferência que exige revisão humana');

INSERT INTO document_availability(document_id, status)
SELECT id, 'available' FROM documents;

CREATE VIEW ranked_entity_claims AS
SELECT claim.*,
       COALESCE(authority.authority_rank, 0) AS effective_authority_rank,
       dense_rank() OVER (
           PARTITION BY claim.subject_entity_id, claim.predicate_id,
                        COALESCE(claim.continuity_id, -1)
           ORDER BY COALESCE(authority.authority_rank, 0) DESC,
                    claim.confidence DESC
       ) AS authority_position
FROM entity_claims AS claim
LEFT JOIN authority_sources AS authority
       ON authority.id = claim.authority_source_id;
"""


MIGRATION_007 = r"""
-- Governança humana, redirects de identidade e semântica temporal dos claims.
CREATE TABLE approval_statuses (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    is_queryable    INTEGER NOT NULL CHECK (is_queryable IN (0, 1)),
    is_terminal     INTEGER NOT NULL CHECK (is_terminal IN (0, 1))
) STRICT;

CREATE TABLE knowledge_proposals (
    id                  INTEGER PRIMARY KEY,
    proposal_uid        TEXT NOT NULL UNIQUE,
    proposal_kind       TEXT NOT NULL CHECK (
        proposal_kind IN ('entity', 'alias', 'relationship', 'state', 'claim')
    ),
    payload_json        TEXT NOT NULL CHECK (json_valid(payload_json)),
    source_scene_uid    TEXT,
    source_excerpt      TEXT,
    extraction_method   TEXT NOT NULL,
    model_name          TEXT,
    model_config_hash   TEXT CHECK (
        model_config_hash IS NULL OR length(model_config_hash) = 64
    ),
    prompt_hash         TEXT CHECK (prompt_hash IS NULL OR length(prompt_hash) = 64),
    confidence          REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    status_id           INTEGER NOT NULL REFERENCES approval_statuses(id),
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE knowledge_approval_decisions (
    id              INTEGER PRIMARY KEY,
    decision_uid    TEXT NOT NULL UNIQUE,
    proposal_id     INTEGER NOT NULL REFERENCES knowledge_proposals(id) ON DELETE CASCADE,
    from_status_id  INTEGER NOT NULL REFERENCES approval_statuses(id),
    to_status_id    INTEGER NOT NULL REFERENCES approval_statuses(id),
    reviewer        TEXT NOT NULL,
    rationale       TEXT,
    decided_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE entity_redirects (
    source_entity_uid   TEXT PRIMARY KEY,
    target_entity_id    INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    redirect_kind       TEXT NOT NULL CHECK (
        redirect_kind IN ('merged', 'renamed', 'deduplicated')
    ),
    reason              TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(source_entity_uid)) >= 16)
) STRICT, WITHOUT ROWID;

CREATE TABLE entity_identity_operations (
    id                  INTEGER PRIMARY KEY,
    event_uid           TEXT NOT NULL UNIQUE,
    operation           TEXT NOT NULL CHECK (operation IN ('merge', 'split')),
    source_uids_json    TEXT NOT NULL CHECK (json_valid(source_uids_json)),
    result_uids_json    TEXT NOT NULL CHECK (json_valid(result_uids_json)),
    actor               TEXT NOT NULL,
    reason              TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE predicate_value_kinds (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL
) STRICT;

CREATE TABLE claim_predicate_rules (
    predicate_id        INTEGER PRIMARY KEY REFERENCES claim_predicates(id) ON DELETE CASCADE,
    value_kind_id       INTEGER NOT NULL REFERENCES predicate_value_kinds(id),
    cardinality         TEXT NOT NULL CHECK (cardinality IN ('single', 'multiple')),
    temporal_mode       TEXT NOT NULL CHECK (temporal_mode IN ('timeless', 'point', 'interval')),
    unit_code           TEXT,
    allows_entity_object INTEGER NOT NULL DEFAULT 1 CHECK (allows_entity_object IN (0, 1)),
    allows_literal_object INTEGER NOT NULL DEFAULT 1 CHECK (allows_literal_object IN (0, 1))
) STRICT;

ALTER TABLE entity_claims ADD COLUMN valid_from_scene_id INTEGER REFERENCES scenes(id) ON DELETE SET NULL;
ALTER TABLE entity_claims ADD COLUMN valid_to_scene_id INTEGER REFERENCES scenes(id) ON DELETE SET NULL;
ALTER TABLE entity_claims ADD COLUMN supersedes_claim_id INTEGER REFERENCES entity_claims(id) ON DELETE SET NULL;

CREATE INDEX idx_claims_temporal_scope
    ON entity_claims(subject_entity_id, predicate_id, valid_from_scene_id, valid_to_scene_id);

INSERT INTO approval_statuses(code, label, is_queryable, is_terminal) VALUES
    ('suggested', 'Sugerido', 0, 0),
    ('approved', 'Aprovado', 1, 1),
    ('rejected', 'Rejeitado', 0, 1),
    ('superseded', 'Substituído', 0, 1);

INSERT INTO predicate_value_kinds(code, label) VALUES
    ('any', 'Qualquer JSON'),
    ('text', 'Texto'),
    ('number', 'Número'),
    ('boolean', 'Booleano'),
    ('entity', 'Entidade'),
    ('date', 'Data ou rótulo cronológico');
"""


MIGRATIONS: Final[tuple[tuple[int, str, str], ...]] = (
    (1, "schema editorial inicial, FTS5 e metadados vetoriais", MIGRATION_001),
    (2, "identidades estáveis, passages, grafo e proveniência", MIGRATION_002),
    (3, "identidade de capítulos e controle de materializações", MIGRATION_003),
    (4, "Merkle DAG editorial com roots separados por domínio", MIGRATION_004),
    (5, "documento editorial ativo e cache de embeddings", MIGRATION_005),
    (6, "confiabilidade, genealogia e proveniência do conhecimento", MIGRATION_006),
    (7, "governança humana, identidade e claims temporais", MIGRATION_007),
)


def database_path(book_dir: str | Path) -> Path:
    """Retorna o caminho convencional do índice sem criar diretórios."""

    return Path(book_dir).expanduser().resolve() / DB_FILENAME


def _pragma_int(connection: sqlite3.Connection, name: str, value: int) -> None:
    # PRAGMA não aceita placeholders; nome é interno e valor já foi validado como int.
    connection.execute(f"PRAGMA {name} = {int(value)}")


def connect(
    db_path: str | Path,
    *,
    read_only: bool = False,
    settings: DatabaseSettings | None = None,
) -> sqlite3.Connection:
    """Abre uma conexão configurada para concorrência local e falha segura.

    Escritores usam WAL + ``synchronous=NORMAL``. Leitores podem abrir em modo
    URI ``mode=ro`` e ainda enxergam commits presentes no WAL.
    """

    settings = settings or DatabaseSettings()
    path = Path(db_path).expanduser().resolve()
    if read_only:
        connection = sqlite3.connect(
            path.as_uri() + "?mode=ro",
            uri=True,
            timeout=settings.busy_timeout_ms / 1_000,
            isolation_level=None,
        )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            path,
            timeout=settings.busy_timeout_ms / 1_000,
            isolation_level=None,
        )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    _pragma_int(connection, "busy_timeout", settings.busy_timeout_ms)
    _pragma_int(connection, "mmap_size", settings.mmap_size)
    connection.execute("PRAGMA temp_store = MEMORY")

    if not read_only:
        journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        if str(journal_mode).lower() != "wal":
            connection.close()
            raise DatabaseEngineError(f"SQLite não ativou WAL em {path}: {journal_mode}")
        connection.execute("PRAGMA synchronous = NORMAL")
        _pragma_int(connection, "wal_autocheckpoint", settings.wal_autocheckpoint_pages)

    return connection


@contextmanager
def transaction(
    connection: sqlite3.Connection,
    *,
    immediate: bool = True,
) -> Iterator[sqlite3.Connection]:
    """Executa uma unidade atômica; ``IMMEDIATE`` evita conflito tardio de escrita."""

    if connection.in_transaction:
        raise DatabaseEngineError("transações aninhadas não são suportadas")
    connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
    try:
        yield connection
    except BaseException:
        connection.rollback()
        raise
    else:
        connection.commit()


def _current_schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def migrate(connection: sqlite3.Connection) -> int:
    """Aplica migrações pendentes e devolve a versão final do schema."""

    current = _current_schema_version(connection)
    if current > LATEST_SCHEMA_VERSION:
        raise SchemaVersionError(
            f"schema v{current} é mais novo que o suportado (v{LATEST_SCHEMA_VERSION})"
        )

    for version, description, sql in MIGRATIONS:
        if version <= current:
            continue
        # executescript controla seus próprios limites; BEGIN/COMMIT no script
        # garante que DDL, seeds e marcador de versão avancem juntos.
        escaped_description = description.replace("'", "''")
        try:
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                + sql
                + f"\nINSERT INTO schema_migrations(version, description) "
                f"VALUES ({version}, '{escaped_description}');\n"
                + f"PRAGMA user_version = {version};\nCOMMIT;"
            )
        except sqlite3.Error:
            if connection.in_transaction:
                connection.rollback()
            raise
        current = version
    return current


def initialize_book_database(
    book_dir: str | Path,
    *,
    slug: str | None = None,
    title: str | None = None,
    settings: DatabaseSettings | None = None,
) -> Path:
    """Cria/migra o índice do livro e registra sua única raiz canônica."""

    root = Path(book_dir).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"pasta do livro não encontrada: {root}")

    db_path = database_path(root)
    connection = connect(db_path, settings=settings)
    try:
        migrate(connection)
        with transaction(connection):
            connection.execute(
                """
                INSERT INTO books(id, slug, title, canonical_root)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    slug = excluded.slug,
                    title = COALESCE(excluded.title, books.title),
                    canonical_root = excluded.canonical_root,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (slug or root.name, title, str(root)),
            )
            work_row = connection.execute(
                "SELECT id FROM works ORDER BY id LIMIT 1"
            ).fetchone()
            if work_row is None:
                effective_slug = slug or root.name
                work_id = connection.execute(
                    """
                    INSERT INTO works(work_uid, title)
                    VALUES (?, ?)
                    """,
                    (f"urn:book:{effective_slug}", title or effective_slug),
                ).lastrowid
                connection.execute(
                    """
                    INSERT INTO editions(
                        work_id, edition_uid, label, is_working_edition
                    ) VALUES (?, ?, 'Edição de trabalho', 1)
                    """,
                    (work_id, f"urn:book:{effective_slug}:working"),
                )
            elif title is not None:
                connection.execute(
                    "UPDATE works SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (title, work_row["id"]),
                )
        connection.execute("PRAGMA optimize")
    finally:
        connection.close()
    return db_path


def _load_sqlite_extension(
    connection: sqlite3.Connection,
    loader: Callable[[sqlite3.Connection], None],
) -> None:
    try:
        connection.enable_load_extension(True)
    except AttributeError as exc:
        raise DatabaseEngineError(
            "este build do Python/SQLite não permite carregar extensões"
        ) from exc
    try:
        loader(connection)
    finally:
        connection.enable_load_extension(False)


def enable_sqlite_vec(
    connection: sqlite3.Connection,
    *,
    dimensions: int,
    loader: Callable[[sqlite3.Connection], None],
) -> None:
    """Carrega sqlite-vec e cria o índice vetorial opcional por cena.

    Mantido para compatibilidade. Novas ingestões devem preferir
    :func:`enable_passage_sqlite_vec`.
    """

    if not 1 <= dimensions <= 65_536:
        raise ValueError("dimensions deve estar entre 1 e 65536")
    _load_sqlite_extension(connection, loader)
    connection.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS scene_vectors USING vec0(
            scene_id INTEGER PRIMARY KEY,
            embedding FLOAT[{dimensions}] DISTANCE_METRIC=cosine
        )
        """
    )


def enable_passage_sqlite_vec(
    connection: sqlite3.Connection,
    *,
    dimensions: int,
    loader: Callable[[sqlite3.Connection], None],
) -> None:
    """Cria o índice vec0 recomendado para recuperação por passagem.

    Use este índice para RAG. ``enable_sqlite_vec`` permanece disponível para
    bancos que ainda tenham embeddings históricos agregados por cena.
    """

    if not 1 <= dimensions <= 65_536:
        raise ValueError("dimensions deve estar entre 1 e 65536")
    _load_sqlite_extension(connection, loader)
    connection.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS passage_vectors USING vec0(
            passage_id INTEGER PRIMARY KEY,
            embedding FLOAT[{dimensions}] DISTANCE_METRIC=cosine
        )
        """
    )


def verify_integrity(connection: sqlite3.Connection) -> None:
    """Levanta exceção se integridade física ou chaves estrangeiras falharem."""

    integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
    if integrity != "ok":
        raise DatabaseEngineError(f"quick_check falhou: {integrity}")
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise DatabaseEngineError(f"foreign_key_check encontrou {len(violations)} violação(ões)")


def quote_fts_query(text: str) -> str:
    """Converte texto livre em uma consulta FTS5 AND, sem aceitar operadores."""

    terms = re.findall(r"[\wÀ-ÖØ-öø-ÿ]+", text, flags=re.UNICODE)
    return " AND ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
