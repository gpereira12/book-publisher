"""Primitivas operacionais para tornar o índice derivado recuperável e auditável."""

from __future__ import annotations

import os
import argparse
import json
import shutil
import sqlite3
import tempfile
import time
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from shared.db_engine import DB_FILENAME, connect, database_path, transaction


class WriterLeaseError(RuntimeError):
    """Outro processo ainda possui o lease exclusivo do escritor."""


@contextmanager
def writer_lease(
    db_path: str | Path,
    *,
    lease_name: str,
    ttl_seconds: int = 3600,
) -> Iterator[str]:
    """Adquire um lease renovável; leases expirados são recuperados atomicamente."""

    if ttl_seconds < 5:
        raise ValueError("ttl_seconds deve ser >= 5")
    owner_id = str(uuid.uuid4())
    connection = connect(db_path)
    now = int(time.time())
    try:
        with transaction(connection):
            connection.execute(
                "DELETE FROM writer_leases WHERE lease_name = ? AND expires_at_epoch <= ?",
                (lease_name, now),
            )
            try:
                connection.execute(
                    """INSERT INTO writer_leases(
                           lease_name, owner_id, acquired_at_epoch,
                           heartbeat_at_epoch, expires_at_epoch
                       ) VALUES (?, ?, ?, ?, ?)""",
                    (lease_name, owner_id, now, now, now + ttl_seconds),
                )
            except sqlite3.IntegrityError as exc:
                holder = connection.execute(
                    "SELECT owner_id, expires_at_epoch FROM writer_leases WHERE lease_name = ?",
                    (lease_name,),
                ).fetchone()
                raise WriterLeaseError(
                    f"lease {lease_name!r} ocupado por {holder['owner_id']} "
                    f"até epoch {holder['expires_at_epoch']}"
                ) from exc
        stop_heartbeat = threading.Event()
        heartbeat_errors: list[BaseException] = []

        def renew() -> None:
            interval = max(1.0, min(float(ttl_seconds) / 3.0, 30.0))
            while not stop_heartbeat.wait(interval):
                heartbeat_connection = connect(db_path)
                try:
                    with transaction(heartbeat_connection):
                        heartbeat_writer_lease(
                            heartbeat_connection,
                            lease_name=lease_name,
                            owner_id=owner_id,
                            ttl_seconds=ttl_seconds,
                        )
                except BaseException as exc:  # comunicado ao escritor no encerramento
                    heartbeat_errors.append(exc)
                    return
                finally:
                    heartbeat_connection.close()

        heartbeat_thread = threading.Thread(
            target=renew,
            name=f"book-lease-{lease_name}",
            daemon=True,
        )
        heartbeat_thread.start()
        body_failed = False
        try:
            yield owner_id
        except BaseException:
            body_failed = True
            raise
        finally:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=5)
        if heartbeat_errors and not body_failed:
            raise WriterLeaseError("falha ao renovar writer lease") from heartbeat_errors[0]
    finally:
        try:
            with transaction(connection):
                connection.execute(
                    "DELETE FROM writer_leases WHERE lease_name = ? AND owner_id = ?",
                    (lease_name, owner_id),
                )
        finally:
            connection.close()


def heartbeat_writer_lease(
    connection: sqlite3.Connection,
    *,
    lease_name: str,
    owner_id: str,
    ttl_seconds: int = 3600,
) -> None:
    now = int(time.time())
    cursor = connection.execute(
        """UPDATE writer_leases
           SET heartbeat_at_epoch = ?, expires_at_epoch = ?
           WHERE lease_name = ? AND owner_id = ? AND expires_at_epoch > ?""",
        (now, now + ttl_seconds, lease_name, owner_id, now),
    )
    if cursor.rowcount != 1:
        raise WriterLeaseError("lease expirou ou pertence a outro escritor")


@contextmanager
def recorded_sync_attempt(
    db_path: str | Path,
    *,
    document_relative_path: str,
    source_sha256: str | None,
    parser_version: str | None,
) -> Iterator[int]:
    """Persiste a tentativa em commits curtos, fora da transação de ingestão."""

    connection = connect(db_path)
    try:
        with transaction(connection):
            attempt_id = connection.execute(
                """INSERT INTO sync_attempts(
                       document_relative_path, source_sha256, parser_version, status
                   ) VALUES (?, ?, ?, 'running')""",
                (document_relative_path, source_sha256, parser_version),
            ).lastrowid
    finally:
        connection.close()
    try:
        yield int(attempt_id)
    except BaseException as exc:
        connection = connect(db_path)
        try:
            with transaction(connection):
                connection.execute(
                    """UPDATE sync_attempts SET status = 'failed',
                           completed_at = CURRENT_TIMESTAMP, error_type = ?, error_message = ?
                       WHERE id = ?""",
                    (type(exc).__name__, str(exc)[:4000], attempt_id),
                )
        finally:
            connection.close()
        raise
    else:
        connection = connect(db_path)
        try:
            with transaction(connection):
                connection.execute(
                    """UPDATE sync_attempts SET status = 'completed',
                           completed_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (attempt_id,),
                )
        finally:
            connection.close()


@dataclass(frozen=True, slots=True)
class ReconcileReport:
    available: int
    missing: int
    deactivated: int


def reconcile_documents(book_dir: str | Path) -> ReconcileReport:
    """Marca fontes ausentes e impede que documentos desaparecidos sejam consultados."""

    root = Path(book_dir).expanduser().resolve()
    connection = connect(database_path(root))
    available = missing = deactivated = 0
    try:
        with transaction(connection):
            for row in connection.execute("SELECT id, relative_path FROM documents"):
                exists = (root / row["relative_path"]).is_file()
                status = "available" if exists else "missing"
                available += int(exists)
                missing += int(not exists)
                connection.execute(
                    """INSERT INTO document_availability(document_id, status, missing_since)
                       VALUES (?, ?, CASE WHEN ? = 'missing' THEN CURRENT_TIMESTAMP END)
                       ON CONFLICT(document_id) DO UPDATE SET
                           status = excluded.status, checked_at = CURRENT_TIMESTAMP,
                           missing_since = CASE
                               WHEN excluded.status = 'available' THEN NULL
                               WHEN document_availability.missing_since IS NULL
                                   THEN CURRENT_TIMESTAMP
                               ELSE document_availability.missing_since END""",
                    (row["id"], status, status),
                )
                if not exists:
                    cursor = connection.execute(
                        """UPDATE edition_document_assignments SET is_active = 0
                           WHERE document_id = ? AND is_active = 1""",
                        (row["id"],),
                    )
                    deactivated += max(cursor.rowcount, 0)
            inactive_roles = connection.execute(
                """SELECT DISTINCT assignment.edition_id, assignment.document_role_id
                   FROM edition_document_assignments AS assignment
                   WHERE NOT EXISTS (
                       SELECT 1 FROM edition_document_assignments AS active
                       WHERE active.edition_id = assignment.edition_id
                         AND active.document_role_id = assignment.document_role_id
                         AND active.is_active = 1
                   )"""
            ).fetchall()
            for role in inactive_roles:
                fallback = connection.execute(
                    """SELECT assignment.document_id
                       FROM edition_document_assignments AS assignment
                       JOIN document_availability AS availability
                            ON availability.document_id = assignment.document_id
                       WHERE assignment.edition_id = ?
                         AND assignment.document_role_id = ?
                         AND availability.status = 'available'
                       ORDER BY assignment.assigned_at DESC, assignment.document_id DESC
                       LIMIT 1""",
                    (role["edition_id"], role["document_role_id"]),
                ).fetchone()
                if fallback:
                    connection.execute(
                        "UPDATE edition_document_assignments SET is_active = 1 WHERE document_id = ?",
                        (fallback[0],),
                    )
    finally:
        connection.close()
    return ReconcileReport(available, missing, deactivated)


def rebuild_book_index(
    book_dir: str | Path,
    *,
    backup: bool = True,
) -> Path:
    """Reconstrói todos os manuscritos conhecidos e troca o DB de forma atômica."""

    from shared.sync_engine import _sync_book_unlocked

    root = Path(book_dir).expanduser().resolve()
    target = database_path(root)
    source_paths: list[tuple[str, str | None]] = []
    knowledge_paths: list[str] = []
    if target.exists():
        connection = connect(target)
        try:
            source_paths = [
                (row[0], row[1])
                for row in connection.execute(
                    """SELECT document.relative_path, role.code
                       FROM documents AS document
                       LEFT JOIN edition_document_assignments AS assignment
                            ON assignment.document_id = document.id
                       LEFT JOIN document_roles AS role ON role.id = assignment.document_role_id
                       ORDER BY document.relative_path"""
                )
                if (root / row[0]).is_file() and str(row[0]).lower().endswith(".md")
            ]
            knowledge_paths = [
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT relative_path FROM knowledge_ingestion_runs WHERE status = 'completed'"
                )
                if (root / row[0]).is_file()
            ]
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            connection.close()
    if not source_paths:
        source_paths = [
            (path.relative_to(root).as_posix(), None)
            for path in sorted(root.glob("*.md"))
            if path.is_file()
        ]
    if not source_paths:
        raise FileNotFoundError("nenhum manuscrito Markdown disponível para rebuild")

    with tempfile.TemporaryDirectory(prefix=".book-rebuild-", dir=root) as temp_name:
        staging_root = Path(temp_name)
        for relative_path, document_role in source_paths:
            source = root / relative_path
            destination = staging_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            _sync_book_unlocked(
                staging_root, manuscript=relative_path, document_role=document_role
            )
        if knowledge_paths:
            from shared.knowledge_sync import sync_knowledge_yaml

            for relative_path in knowledge_paths:
                source = root / relative_path
                destination = staging_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                sync_knowledge_yaml(staging_root, yaml_path=relative_path)
        governance_log = root / "knowledge_reviews.jsonl"
        if governance_log.is_file():
            shutil.copy2(governance_log, staging_root / governance_log.name)
            from shared.knowledge_governance import replay_governance_log

            replay_governance_log(staging_root, db_path=staging_root / DB_FILENAME)
        staging_db = staging_root / DB_FILENAME
        staging_connection = connect(staging_db)
        try:
            staging_connection.execute(
                "UPDATE books SET canonical_root = ? WHERE id = 1", (str(root),)
            )
            staging_connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            staging_connection.close()
        if backup and target.exists():
            backup_path = target.with_name(f"{target.name}.backup-{time.time_ns()}")
            source_connection = connect(target, read_only=True)
            backup_connection = sqlite3.connect(backup_path)
            try:
                source_connection.backup(backup_connection)
            finally:
                backup_connection.close()
                source_connection.close()
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(target) + suffix)
            if sidecar.exists():
                sidecar.unlink()
        os.replace(staging_db, target)
    return target


@dataclass(frozen=True, slots=True)
class BackupVerification:
    path: str
    integrity: str
    foreign_key_violations: int
    schema_version: int


def verify_database_backup(backup_path: str | Path) -> BackupVerification:
    path = Path(backup_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = connect(path, read_only=True)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        violations = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    finally:
        connection.close()
    if integrity != "ok" or violations:
        raise RuntimeError(
            f"backup inválido: integrity={integrity}, foreign_keys={violations}"
        )
    return BackupVerification(str(path), integrity, violations, version)


def restore_book_index(
    book_dir: str | Path,
    *,
    backup_path: str | Path,
    preserve_current: bool = True,
) -> Path:
    """Valida, copia e troca um backup sem modificar a fonte canônica."""

    root = Path(book_dir).expanduser().resolve()
    target = database_path(root)
    verified = verify_database_backup(backup_path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".book-restore-", suffix=".db", dir=root
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        source_connection = connect(verified.path, read_only=True)
        target_connection = sqlite3.connect(temporary)
        try:
            source_connection.backup(target_connection)
        finally:
            target_connection.close()
            source_connection.close()
        verify_database_backup(temporary)
        if preserve_current and target.exists():
            current_backup = target.with_name(
                f"{target.name}.backup-before-restore-{time.time_ns()}"
            )
            current_connection = connect(target, read_only=True)
            backup_connection = sqlite3.connect(current_backup)
            try:
                current_connection.backup(backup_connection)
            finally:
                backup_connection.close()
                current_connection.close()
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(target) + suffix)
            if sidecar.exists():
                sidecar.unlink()
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def prune_database_backups(
    book_dir: str | Path,
    *,
    keep: int = 5,
) -> list[str]:
    """Remove somente backups convencionais excedentes; nunca toca o DB ativo."""

    if keep < 1:
        raise ValueError("keep deve ser >= 1")
    root = Path(book_dir).expanduser().resolve()
    backups = sorted(
        root.glob(f"{DB_FILENAME}.backup-*"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    removed: list[str] = []
    for backup in backups[keep:]:
        if backup.is_file() and backup.parent == root and backup.name.startswith(
            f"{DB_FILENAME}.backup-"
        ):
            backup.unlink()
            removed.append(str(backup))
    return removed


def record_scene_lineage(
    db_path: str | Path,
    *,
    parent_scene_uid: str,
    child_scene_uid: str,
    lineage_type: str = "derived_from",
    confidence: float = 1.0,
    notes: str | None = None,
) -> None:
    connection = connect(db_path)
    try:
        with transaction(connection):
            type_row = connection.execute(
                "SELECT id FROM scene_lineage_types WHERE code = ?", (lineage_type,)
            ).fetchone()
            if type_row is None:
                raise KeyError(f"tipo de linhagem desconhecido: {lineage_type}")
            connection.execute(
                """INSERT INTO scene_lineage(
                       parent_scene_uid, child_scene_uid, lineage_type_id,
                       confidence, notes
                   ) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(parent_scene_uid, child_scene_uid, lineage_type_id)
                   DO UPDATE SET confidence = excluded.confidence, notes = excluded.notes""",
                (parent_scene_uid, child_scene_uid, type_row[0], confidence, notes),
            )
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Operações de confiabilidade do índice")
    subparsers = parser.add_subparsers(dest="command", required=True)
    reconcile = subparsers.add_parser("reconcile")
    reconcile.add_argument("book_dir")
    rebuild = subparsers.add_parser("rebuild")
    rebuild.add_argument("book_dir")
    rebuild.add_argument("--no-backup", action="store_true")
    verify = subparsers.add_parser("verify-backup")
    verify.add_argument("backup_path")
    restore = subparsers.add_parser("restore")
    restore.add_argument("book_dir")
    restore.add_argument("backup_path")
    restore.add_argument("--discard-current", action="store_true")
    prune = subparsers.add_parser("prune-backups")
    prune.add_argument("book_dir")
    prune.add_argument("--keep", type=int, default=5)
    args = parser.parse_args()
    if args.command == "reconcile":
        report = reconcile_documents(args.book_dir)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    elif args.command == "rebuild":
        print(rebuild_book_index(args.book_dir, backup=not args.no_backup))
    elif args.command == "verify-backup":
        print(json.dumps(asdict(verify_database_backup(args.backup_path)), indent=2))
    elif args.command == "restore":
        print(restore_book_index(
            args.book_dir,
            backup_path=args.backup_path,
            preserve_current=not args.discard_current,
        ))
    else:
        print(json.dumps(prune_database_backups(args.book_dir, keep=args.keep), indent=2))


if __name__ == "__main__":
    main()
