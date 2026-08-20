"""Harness Sync Engine incremental para manuscritos Markdown.

Uso:
    python -m shared.sync_engine inputs/meu_livro
    python -m shared.sync_engine inputs/meu_livro --manuscript texto_original.md --json
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

from shared.db_engine import connect, initialize_book_database, transaction
from shared.markdown_scene_parser import PARSER_VERSION, ChapterDraft, SceneDraft, parse_markdown
from shared.merkle import MerkleRootSet, refresh_document_merkle_roots


_UID_NAMESPACE: Final = uuid.UUID("3fb3a540-d7a1-4cd0-b5f8-c45171fa0c50")


class SyncEngineError(RuntimeError):
    """Falha de contrato ou integridade durante a sincronização."""


@dataclass(frozen=True, slots=True)
class SyncReport:
    database_path: str
    manuscript_path: str
    source_sha256: str
    skipped: bool
    chapters: int
    inserted_scenes: int
    updated_scenes: int
    unchanged_scenes: int
    deleted_scenes: int
    passages: int
    content_merkle_root: str
    structure_merkle_root: str
    materialization_merkle_root: str


def _parser_signature(
    chapter_heading_level: int | None,
    passage_target_words: int,
    passage_overlap_paragraphs: int,
) -> str:
    heading = "auto" if chapter_heading_level is None else str(chapter_heading_level)
    return (
        f"{PARSER_VERSION};heading={heading};words={passage_target_words};"
        f"overlap={passage_overlap_paragraphs}"
    )


def _resolve_manuscript(book_dir: Path, manuscript: str | Path | None) -> Path:
    if manuscript is None:
        revised = book_dir / "texto_revisado.md"
        path = revised if revised.exists() else book_dir / "texto_original.md"
    else:
        candidate = Path(manuscript).expanduser()
        path = candidate if candidate.is_absolute() else book_dir / candidate
    path = path.resolve()
    try:
        path.relative_to(book_dir)
    except ValueError as exc:
        raise SyncEngineError("o manuscrito deve estar dentro da pasta do livro") from exc
    if not path.is_file():
        raise FileNotFoundError(f"manuscrito não encontrado: {path}")
    return path


def _infer_document_role(relative_path: str) -> str:
    lowered = relative_path.lower()
    if "revisado" in lowered or "revised" in lowered:
        return "working_revision"
    if "traducao" in lowered or "tradução" in lowered or "translation" in lowered:
        return "translation"
    return "source_original"


def _uuid(kind: str, work_uid: str, relative_path: str, stable_key: str) -> str:
    return str(
        uuid.uuid5(
            _UID_NAMESPACE,
            f"{kind}:{work_uid}:{relative_path}:{stable_key}",
        )
    )


def _unique_hash_rows(rows: list[sqlite3.Row]) -> dict[str, sqlite3.Row]:
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["content_sha256"], []).append(row)
    return {digest: matches[0] for digest, matches in grouped.items() if len(matches) == 1}


def _revision_patch(old: str, new: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile="scene:before",
            tofile="scene:after",
            lineterm="",
        )
    )


def _upsert_derivation_status(
    connection: sqlite3.Connection,
    scene_id: int,
    kind_code: str,
    status_code: str,
    source_sha256: str,
    *,
    generated: bool = False,
) -> None:
    connection.execute(
        """
        INSERT INTO scene_derivation_status(
            scene_id, derivation_kind_id, status_id, source_sha256, generated_at
        )
        SELECT ?, kind.id, status.id, ?,
               CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END
        FROM derivation_kinds AS kind
        CROSS JOIN derivation_statuses AS status
        WHERE kind.code = ? AND status.code = ?
        ON CONFLICT(scene_id, derivation_kind_id) DO UPDATE SET
            status_id = excluded.status_id,
            source_sha256 = excluded.source_sha256,
            generated_at = excluded.generated_at
        """,
        (
            scene_id,
            source_sha256,
            int(generated),
            kind_code,
            status_code,
        ),
    )


def _sync_passages(
    connection: sqlite3.Connection,
    scene_id: int,
    scene: SceneDraft,
    *,
    passage_vectors_exist: bool,
) -> tuple[int, bool]:
    existing = connection.execute(
        "SELECT * FROM passages WHERE scene_id = ? ORDER BY ordinal", (scene_id,)
    ).fetchall()
    by_ordinal = {row["ordinal"]: row for row in existing}
    if existing:
        connection.execute(
            "UPDATE passages SET ordinal = ordinal + 100000 WHERE scene_id = ?",
            (scene_id,),
        )

    retained: set[int] = set()
    embeddings_stale = False
    for passage in scene.passages:
        old = by_ordinal.get(passage.ordinal)
        if old is None:
            connection.execute(
                """
                INSERT INTO passages(
                    scene_id, ordinal, start_offset, end_offset, start_line,
                    end_line, content, content_sha256, token_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scene_id,
                    passage.ordinal,
                    passage.start_offset,
                    passage.end_offset,
                    passage.start_line,
                    passage.end_line,
                    passage.content,
                    passage.content_sha256,
                    passage.token_count,
                ),
            )
            embeddings_stale = True
            continue

        passage_id = old["id"]
        retained.add(passage_id)
        changed = old["content_sha256"] != passage.content_sha256
        connection.execute(
            """
            UPDATE passages SET
                ordinal = ?, start_offset = ?, end_offset = ?, start_line = ?,
                end_line = ?, content = ?, content_sha256 = ?, token_count = ?,
                indexed_at = CASE WHEN content_sha256 <> ? THEN CURRENT_TIMESTAMP ELSE indexed_at END
            WHERE id = ?
            """,
            (
                passage.ordinal,
                passage.start_offset,
                passage.end_offset,
                passage.start_line,
                passage.end_line,
                passage.content,
                passage.content_sha256,
                passage.token_count,
                passage.content_sha256,
                passage_id,
            ),
        )
        if changed:
            embeddings_stale = True
            connection.execute(
                "DELETE FROM passage_embedding_sources WHERE passage_id = ?",
                (passage_id,),
            )
            if passage_vectors_exist:
                connection.execute(
                    "DELETE FROM passage_vectors WHERE passage_id = ?", (passage_id,)
                )

    removed = [row["id"] for row in existing if row["id"] not in retained]
    if removed:
        embeddings_stale = True
        placeholders = ",".join("?" for _ in removed)
        if passage_vectors_exist:
            connection.execute(
                f"DELETE FROM passage_vectors WHERE passage_id IN ({placeholders})",
                removed,
            )
        connection.execute(f"DELETE FROM passages WHERE id IN ({placeholders})", removed)

    _upsert_derivation_status(
        connection,
        scene_id,
        "passages",
        "fresh",
        scene.content_sha256,
        generated=True,
    )
    if embeddings_stale:
        _upsert_derivation_status(
            connection, scene_id, "embeddings", "pending", scene.content_sha256
        )
    return len(scene.passages), embeddings_stale


def _choose_chapter_row(
    chapter: ChapterDraft,
    by_uid: dict[str, sqlite3.Row],
    by_key: dict[str, sqlite3.Row],
    claimed: set[int],
) -> sqlite3.Row | None:
    candidates = []
    if chapter.declared_uid:
        candidates.append(by_uid.get(chapter.declared_uid))
    candidates.append(by_key.get(chapter.stable_key))
    return next((row for row in candidates if row is not None and row["id"] not in claimed), None)


def _choose_scene_row(
    scene: SceneDraft,
    chapter_key: str,
    by_uid: dict[str, sqlite3.Row],
    by_local_key: dict[tuple[str, str], sqlite3.Row],
    by_unique_hash: dict[str, sqlite3.Row],
    claimed: set[int],
) -> sqlite3.Row | None:
    candidates = []
    if scene.declared_uid:
        candidates.append(by_uid.get(scene.declared_uid))
    candidates.extend(
        [
            by_local_key.get((chapter_key, scene.stable_key)),
            by_unique_hash.get(scene.content_sha256),
        ]
    )
    return next((row for row in candidates if row is not None and row["id"] not in claimed), None)


def _sync_book_unlocked(
    book_dir: str | Path,
    *,
    manuscript: str | Path | None = None,
    chapter_heading_level: int | None = None,
    passage_target_words: int = 350,
    passage_overlap_paragraphs: int = 1,
    document_role: str | None = None,
) -> SyncReport:
    """Sincroniza um manuscrito e atualiza somente materializações afetadas."""

    root = Path(book_dir).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"pasta do livro não encontrada: {root}")
    manuscript_path = _resolve_manuscript(root, manuscript)
    relative_path = manuscript_path.relative_to(root).as_posix()
    effective_document_role = document_role or _infer_document_role(relative_path)
    raw = manuscript_path.read_bytes()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    signature = _parser_signature(
        chapter_heading_level, passage_target_words, passage_overlap_paragraphs
    )
    db_path = initialize_book_database(root)
    connection = connect(db_path)
    try:
        existing_document = connection.execute(
            """SELECT document.id, document.content_sha256,
                      document.parser_version, role.code AS role_code,
                      assignment.is_active
               FROM documents AS document
               LEFT JOIN edition_document_assignments AS assignment
                    ON assignment.document_id = document.id
               LEFT JOIN document_roles AS role ON role.id = assignment.document_role_id
               WHERE document.book_id = 1 AND document.relative_path = ?""",
            (relative_path,),
        ).fetchone()
        existing_roots: dict[str, str] = {}
        if existing_document is not None:
            existing_roots = {
                row["code"]: row["root_hash"]
                for row in connection.execute(
                    """SELECT kind.code, root.root_hash
                       FROM document_merkle_roots AS root
                       JOIN merkle_root_kinds AS kind ON kind.id = root.root_kind_id
                       WHERE root.document_id = ?""",
                    (existing_document["id"],),
                )
            }
        if (
            existing_document is not None
            and existing_document["content_sha256"] == source_sha256
            and existing_document["parser_version"] == signature
            and existing_document["role_code"] == effective_document_role
            and existing_document["is_active"] == 1
            and all(
                code in existing_roots
                for code in ("content", "structure", "materialization")
            )
        ):
            counts = connection.execute(
                """SELECT count(DISTINCT c.id), count(DISTINCT s.id), count(DISTINCT p.id)
                   FROM documents AS d
                   LEFT JOIN chapters AS c ON c.document_id = d.id
                   LEFT JOIN scenes AS s ON s.chapter_id = c.id
                   LEFT JOIN passages AS p ON p.scene_id = s.id
                   WHERE d.id = ?""",
                (existing_document["id"],),
            ).fetchone()
            return SyncReport(
                database_path=str(db_path),
                manuscript_path=str(manuscript_path),
                source_sha256=source_sha256,
                skipped=True,
                chapters=counts[0],
                inserted_scenes=0,
                updated_scenes=0,
                unchanged_scenes=counts[1],
                deleted_scenes=0,
                passages=counts[2],
                content_merkle_root=existing_roots["content"],
                structure_merkle_root=existing_roots["structure"],
                materialization_merkle_root=existing_roots["materialization"],
            )

        parsed = parse_markdown(
            manuscript_path,
            chapter_heading_level=chapter_heading_level,
            passage_target_words=passage_target_words,
            passage_overlap_paragraphs=passage_overlap_paragraphs,
        )
        stat = manuscript_path.stat()
        inserted = updated = unchanged = deleted = passage_count = 0

        with transaction(connection):
            edition_id = connection.execute(
                "SELECT id FROM editions WHERE is_working_edition = 1 ORDER BY id LIMIT 1"
            ).fetchone()[0]
            work_uid = connection.execute(
                """SELECT w.work_uid FROM works AS w
                   JOIN editions AS e ON e.work_id = w.id WHERE e.id = ?""",
                (edition_id,),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO documents(
                    book_id, kind, relative_path, edition_id, parser_version
                ) VALUES (1, 'manuscript', ?, ?, ?)
                ON CONFLICT(book_id, relative_path) DO UPDATE SET
                    kind = excluded.kind,
                    edition_id = excluded.edition_id
                """,
                (relative_path, edition_id, signature),
            )
            document_id = connection.execute(
                "SELECT id FROM documents WHERE book_id = 1 AND relative_path = ?",
                (relative_path,),
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO document_availability(document_id, status)
                   VALUES (?, 'available')
                   ON CONFLICT(document_id) DO UPDATE SET
                       status = 'available', checked_at = CURRENT_TIMESTAMP,
                       missing_since = NULL""",
                (document_id,),
            )
            role = connection.execute(
                "SELECT id FROM document_roles WHERE code = ?",
                (effective_document_role,),
            ).fetchone()
            if role is None:
                raise SyncEngineError(
                    f"papel de documento desconhecido: {effective_document_role}"
                )
            connection.execute(
                """UPDATE edition_document_assignments SET is_active = 0
                   WHERE edition_id = ? AND document_role_id = ? AND document_id <> ?""",
                (edition_id, role["id"], document_id),
            )
            connection.execute(
                """
                INSERT INTO edition_document_assignments(
                    document_id, edition_id, document_role_id, is_active
                ) VALUES (?, ?, ?, 1)
                ON CONFLICT(document_id) DO UPDATE SET
                    edition_id = excluded.edition_id,
                    document_role_id = excluded.document_role_id,
                    is_active = 1,
                    assigned_at = CURRENT_TIMESTAMP
                """,
                (document_id, edition_id, role["id"]),
            )
            sync_run_id = connection.execute(
                """INSERT INTO sync_runs(document_id, source_sha256, parser_version, status)
                   VALUES (?, ?, ?, 'running')""",
                (document_id, source_sha256, signature),
            ).lastrowid

            old_chapters = connection.execute(
                "SELECT * FROM chapters WHERE document_id = ?", (document_id,)
            ).fetchall()
            old_scenes = connection.execute(
                """SELECT s.*, c.stable_key AS chapter_stable_key
                   FROM scenes AS s JOIN chapters AS c ON c.id = s.chapter_id
                   WHERE c.document_id = ?""",
                (document_id,),
            ).fetchall()
            chapter_by_uid = {row["chapter_uid"]: row for row in old_chapters}
            chapter_by_key = {row["stable_key"]: row for row in old_chapters}
            scene_by_uid = {row["scene_uid"]: row for row in old_scenes}
            scene_by_local_key = {
                (row["chapter_stable_key"], row["stable_key"]): row for row in old_scenes
            }
            scene_by_hash = _unique_hash_rows(list(old_scenes))

            if old_scenes:
                connection.execute(
                    "UPDATE scenes SET ordinal = ordinal + 100000, stable_key = '__sync_scene_' || id "
                    "WHERE chapter_id IN (SELECT id FROM chapters WHERE document_id = ?)",
                    (document_id,),
                )
            if old_chapters:
                connection.execute(
                    "UPDATE chapters SET ordinal = ordinal + 100000, stable_key = '__sync_chapter_' || id "
                    "WHERE document_id = ?",
                    (document_id,),
                )

            claimed_chapters: set[int] = set()
            chapter_ids: dict[str, int] = {}
            for chapter in parsed.chapters:
                old = _choose_chapter_row(
                    chapter, chapter_by_uid, chapter_by_key, claimed_chapters
                )
                final_uid = chapter.declared_uid or (
                    old["chapter_uid"]
                    if old is not None
                    else _uuid("chapter", work_uid, relative_path, chapter.stable_key)
                )
                if old is None:
                    chapter_id = connection.execute(
                        """INSERT INTO chapters(
                               document_id, ordinal, stable_key, chapter_uid, title,
                               start_line, end_line
                           ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            document_id,
                            chapter.ordinal,
                            chapter.stable_key,
                            final_uid,
                            chapter.title,
                            chapter.start_line,
                            chapter.end_line,
                        ),
                    ).lastrowid
                else:
                    chapter_id = old["id"]
                    claimed_chapters.add(chapter_id)
                    connection.execute(
                        """UPDATE chapters SET
                               ordinal = ?, stable_key = ?, chapter_uid = ?, title = ?,
                               start_line = ?, end_line = ?
                           WHERE id = ?""",
                        (
                            chapter.ordinal,
                            chapter.stable_key,
                            final_uid,
                            chapter.title,
                            chapter.start_line,
                            chapter.end_line,
                            chapter_id,
                        ),
                    )
                chapter_ids[chapter.stable_key] = chapter_id

            passage_vectors_exist = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'passage_vectors'"
            ).fetchone() is not None
            claimed_scenes: set[int] = set()
            for chapter in parsed.chapters:
                chapter_id = chapter_ids[chapter.stable_key]
                for scene in chapter.scenes:
                    old = _choose_scene_row(
                        scene,
                        chapter.stable_key,
                        scene_by_uid,
                        scene_by_local_key,
                        scene_by_hash,
                        claimed_scenes,
                    )
                    final_uid = scene.declared_uid or (
                        old["scene_uid"]
                        if old is not None
                        else _uuid(
                            "scene",
                            work_uid,
                            relative_path,
                            f"{chapter.stable_key}/{scene.stable_key}",
                        )
                    )
                    connection.execute(
                        "UPDATE scene_tombstones SET restored_at = CURRENT_TIMESTAMP WHERE scene_uid = ?",
                        (final_uid,),
                    )
                    if old is None:
                        scene_id = connection.execute(
                            """INSERT INTO scenes(
                                   chapter_id, ordinal, stable_key, scene_uid,
                                   scene_title, start_line, end_line, content,
                                   content_sha256, token_count
                               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                chapter_id,
                                scene.ordinal,
                                scene.stable_key,
                                final_uid,
                                scene.title,
                                scene.start_line,
                                scene.end_line,
                                scene.content,
                                scene.content_sha256,
                                scene.token_count,
                            ),
                        ).lastrowid
                        inserted += 1
                        content_changed = True
                    else:
                        scene_id = old["id"]
                        claimed_scenes.add(scene_id)
                        content_changed = old["content_sha256"] != scene.content_sha256
                        if content_changed:
                            parent = connection.execute(
                                """SELECT id FROM scene_revisions
                                   WHERE scene_id = ? ORDER BY id DESC LIMIT 1""",
                                (scene_id,),
                            ).fetchone()
                            connection.execute(
                                """INSERT INTO scene_revisions(
                                       scene_id, parent_revision_id, base_sha256,
                                       result_sha256, patch_text, author
                                   ) VALUES (?, ?, ?, ?, ?, 'harness-sync')""",
                                (
                                    scene_id,
                                    parent[0] if parent else None,
                                    old["content_sha256"],
                                    scene.content_sha256,
                                    _revision_patch(old["content"], scene.content),
                                ),
                            )
                            updated += 1
                            connection.execute(
                                "DELETE FROM scene_embedding_sources WHERE scene_id = ?",
                                (scene_id,),
                            )
                            for kind in (
                                "embeddings",
                                "mentions",
                                "entity_states",
                                "review_findings",
                                "framework_beats",
                            ):
                                _upsert_derivation_status(
                                    connection,
                                    scene_id,
                                    kind,
                                    "stale",
                                    scene.content_sha256,
                                )
                        else:
                            unchanged += 1
                        connection.execute(
                            """UPDATE scenes SET
                                   chapter_id = ?, ordinal = ?, stable_key = ?,
                                   scene_uid = ?, scene_title = ?, start_line = ?,
                                   end_line = ?, content = ?, content_sha256 = ?,
                                   token_count = ?,
                                   indexed_at = CASE WHEN content_sha256 <> ?
                                                     THEN CURRENT_TIMESTAMP ELSE indexed_at END
                               WHERE id = ?""",
                            (
                                chapter_id,
                                scene.ordinal,
                                scene.stable_key,
                                final_uid,
                                scene.title,
                                scene.start_line,
                                scene.end_line,
                                scene.content,
                                scene.content_sha256,
                                scene.token_count,
                                scene.content_sha256,
                                scene_id,
                            ),
                        )

                    synced_passages, _ = _sync_passages(
                        connection,
                        scene_id,
                        scene,
                        passage_vectors_exist=passage_vectors_exist,
                    )
                    passage_count += synced_passages

            removed_scene_ids = [
                row["id"] for row in old_scenes if row["id"] not in claimed_scenes
            ]
            if removed_scene_ids:
                placeholders = ",".join("?" for _ in removed_scene_ids)
                connection.execute(
                    f"""INSERT INTO scene_tombstones(
                            scene_uid, document_relative_path, chapter_uid,
                            stable_key, scene_title, last_content,
                            last_content_sha256, removal_reason
                        )
                        SELECT s.scene_uid, d.relative_path, c.chapter_uid,
                               s.stable_key, s.scene_title, s.content,
                               s.content_sha256, 'source_removed'
                        FROM scenes AS s
                        JOIN chapters AS c ON c.id = s.chapter_id
                        JOIN documents AS d ON d.id = c.document_id
                        WHERE s.id IN ({placeholders})
                        ON CONFLICT(scene_uid) DO UPDATE SET
                            document_relative_path = excluded.document_relative_path,
                            chapter_uid = excluded.chapter_uid,
                            stable_key = excluded.stable_key,
                            scene_title = excluded.scene_title,
                            last_content = excluded.last_content,
                            last_content_sha256 = excluded.last_content_sha256,
                            removed_at = CURRENT_TIMESTAMP,
                            restored_at = NULL,
                            removal_reason = excluded.removal_reason""",
                    removed_scene_ids,
                )
                connection.execute(
                    f"""INSERT OR IGNORE INTO archived_scene_revisions(
                            original_revision_id, parent_original_revision_id,
                            scene_uid, base_sha256,
                            result_sha256, patch_text, author, created_at
                        )
                        SELECT revision.id, revision.parent_revision_id,
                               scene.scene_uid, revision.base_sha256,
                               revision.result_sha256, revision.patch_text,
                               revision.author, revision.created_at
                        FROM scene_revisions AS revision
                        JOIN scenes AS scene ON scene.id = revision.scene_id
                        WHERE scene.id IN ({placeholders})""",
                    removed_scene_ids,
                )
                connection.execute(
                    f"DELETE FROM scenes WHERE id IN ({placeholders})", removed_scene_ids
                )
                deleted = len(removed_scene_ids)
            removed_chapter_ids = [
                row["id"] for row in old_chapters if row["id"] not in claimed_chapters
            ]
            if removed_chapter_ids:
                placeholders = ",".join("?" for _ in removed_chapter_ids)
                connection.execute(
                    f"DELETE FROM chapters WHERE id IN ({placeholders})", removed_chapter_ids
                )

            connection.execute(
                """UPDATE documents SET
                       content_sha256 = ?, byte_size = ?, modified_ns = ?,
                       parser_version = ?, indexed_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (
                    source_sha256,
                    parsed.byte_size,
                    stat.st_mtime_ns,
                    signature,
                    document_id,
                ),
            )
            merkle_roots: MerkleRootSet = refresh_document_merkle_roots(
                connection, document_id, parser_signature=signature
            )
            connection.execute(
                """UPDATE sync_runs SET
                       inserted_scenes = ?, updated_scenes = ?, unchanged_scenes = ?,
                       deleted_scenes = ?, completed_at = CURRENT_TIMESTAMP,
                       status = 'completed', content_merkle_root = ?,
                       structure_merkle_root = ?, materialization_merkle_root = ?
                   WHERE id = ?""",
                (
                    inserted,
                    updated,
                    unchanged,
                    deleted,
                    merkle_roots.content,
                    merkle_roots.structure,
                    merkle_roots.materialization,
                    sync_run_id,
                ),
            )

        connection.execute("PRAGMA optimize")
        return SyncReport(
            database_path=str(db_path),
            manuscript_path=str(manuscript_path),
            source_sha256=source_sha256,
            skipped=False,
            chapters=len(parsed.chapters),
            inserted_scenes=inserted,
            updated_scenes=updated,
            unchanged_scenes=unchanged,
            deleted_scenes=deleted,
            passages=passage_count,
            content_merkle_root=merkle_roots.content,
            structure_merkle_root=merkle_roots.structure,
            materialization_merkle_root=merkle_roots.materialization,
        )
    finally:
        connection.close()


def sync_book(
    book_dir: str | Path,
    *,
    manuscript: str | Path | None = None,
    chapter_heading_level: int | None = None,
    passage_target_words: int = 350,
    passage_overlap_paragraphs: int = 1,
    document_role: str | None = None,
) -> SyncReport:
    """Executa o sync sob lease exclusivo e registra inclusive tentativas falhas."""

    from shared.reliability import recorded_sync_attempt, writer_lease

    root = Path(book_dir).expanduser().resolve()
    manuscript_path = _resolve_manuscript(root, manuscript)
    relative_path = manuscript_path.relative_to(root).as_posix()
    source_sha256 = hashlib.sha256(manuscript_path.read_bytes()).hexdigest()
    signature = _parser_signature(
        chapter_heading_level, passage_target_words, passage_overlap_paragraphs
    )
    db_path = initialize_book_database(root)
    with writer_lease(db_path, lease_name="harness-sync"):
        with recorded_sync_attempt(
            db_path,
            document_relative_path=relative_path,
            source_sha256=source_sha256,
            parser_version=signature,
        ):
            return _sync_book_unlocked(
                root,
                manuscript=manuscript_path,
                chapter_heading_level=chapter_heading_level,
                passage_target_words=passage_target_words,
                passage_overlap_paragraphs=passage_overlap_paragraphs,
                document_role=document_role,
            )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sincroniza incrementalmente um manuscrito com .book_index.db"
    )
    parser.add_argument("book_dir", help="Pasta inputs/<livro>")
    parser.add_argument("--manuscript", help="Arquivo dentro da pasta do livro")
    parser.add_argument("--chapter-heading-level", type=int, choices=range(1, 7))
    parser.add_argument("--passage-target-words", type=int, default=350)
    parser.add_argument("--passage-overlap-paragraphs", type=int, default=1)
    parser.add_argument(
        "--document-role",
        choices=(
            "source_original",
            "working_revision",
            "approved_manuscript",
            "translation",
        ),
        help="Papel editorial; por padrão é inferido pelo nome do arquivo",
    )
    parser.add_argument("--json", action="store_true", help="Emite relatório JSON")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    report = sync_book(
        args.book_dir,
        manuscript=args.manuscript,
        chapter_heading_level=args.chapter_heading_level,
        passage_target_words=args.passage_target_words,
        passage_overlap_paragraphs=args.passage_overlap_paragraphs,
        document_role=args.document_role,
    )
    payload = asdict(report)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        action = "sem alterações" if report.skipped else "sincronizado"
        print(
            f"{action}: {report.chapters} capítulo(s), "
            f"{report.inserted_scenes} inserida(s), "
            f"{report.updated_scenes} atualizada(s), "
            f"{report.deleted_scenes} removida(s), "
            f"{report.passages} passage(s)"
        )


if __name__ == "__main__":
    main()
