"""Consultas de cena e diagnóstico seguro do índice derivado."""

from __future__ import annotations

from pathlib import Path

from shared.db_engine import connect


def get_scene_context(db_path: str | Path, scene_uid: str) -> dict[str, object]:
    connection = connect(db_path, read_only=True)
    try:
        scene = connection.execute(
            """SELECT scene.id, scene.scene_uid, scene.scene_title,
                      scene.start_line, scene.end_line, scene.content,
                      scene.content_sha256, chapter.chapter_uid,
                      chapter.title AS chapter_title,
                      document.relative_path AS document_path
               FROM scenes AS scene
               JOIN chapters AS chapter ON chapter.id = scene.chapter_id
               JOIN documents AS document ON document.id = chapter.document_id
               WHERE scene.scene_uid = ?""",
            (scene_uid,),
        ).fetchone()
        if scene is None:
            raise LookupError(f"cena não encontrada: {scene_uid}")
        links = [
            dict(row)
            for row in connection.execute(
                """SELECT type.code AS relationship,
                          source.scene_uid AS source_scene_uid,
                          target.scene_uid AS target_scene_uid,
                          link.weight, link.description, link.provenance_kind
                   FROM scene_links AS link
                   JOIN scene_link_types AS type ON type.id = link.scene_link_type_id
                   JOIN scenes AS source ON source.id = link.source_scene_id
                   JOIN scenes AS target ON target.id = link.target_scene_id
                   WHERE link.source_scene_id = ? OR link.target_scene_id = ?
                   ORDER BY type.code, source.scene_uid, target.scene_uid""",
                (scene["id"], scene["id"]),
            )
        ]
        derivations = {
            row["kind"]: {
                "status": row["status"],
                "source_sha256": row["source_sha256"],
                "generated_at": row["generated_at"],
            }
            for row in connection.execute(
                """SELECT kind.code AS kind, status.code AS status,
                          materialization.source_sha256,
                          materialization.generated_at
                   FROM scene_derivation_status AS materialization
                   JOIN derivation_kinds AS kind
                        ON kind.id = materialization.derivation_kind_id
                   JOIN derivation_statuses AS status
                        ON status.id = materialization.status_id
                   WHERE materialization.scene_id = ?""",
                (scene["id"],),
            )
        }
        payload = dict(scene)
        payload.pop("id")
        payload["links"] = links
        payload["derivations"] = derivations
        return payload
    finally:
        connection.close()


def verify_book_index(db_path: str | Path) -> dict[str, object]:
    connection = connect(db_path, read_only=True)
    try:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        foreign_key_violations = len(
            connection.execute("PRAGMA foreign_key_check").fetchall()
        )
        document_roots = [
            dict(row)
            for row in connection.execute(
                """SELECT document.relative_path AS document_path,
                          kind.code AS root_kind, root.root_hash,
                          root.computed_at
                   FROM document_merkle_roots AS root
                   JOIN documents AS document ON document.id = root.document_id
                   JOIN merkle_root_kinds AS kind ON kind.id = root.root_kind_id
                   ORDER BY document.relative_path, kind.code"""
            )
        ]
        derivations = [
            dict(row)
            for row in connection.execute(
                """SELECT kind.code AS kind, status.code AS status, count(*) AS total
                   FROM scene_derivation_status AS materialization
                   JOIN derivation_kinds AS kind
                        ON kind.id = materialization.derivation_kind_id
                   JOIN derivation_statuses AS status
                        ON status.id = materialization.status_id
                   GROUP BY kind.code, status.code
                   ORDER BY kind.code, status.code"""
            )
        ]
        counts = dict(
            connection.execute(
                """SELECT count(DISTINCT chapter.id) AS chapters,
                          count(DISTINCT scene.id) AS scenes,
                          count(DISTINCT passage.id) AS passages
                   FROM chapters AS chapter
                   LEFT JOIN scenes AS scene ON scene.chapter_id = chapter.id
                   LEFT JOIN passages AS passage ON passage.scene_id = scene.id"""
            ).fetchone()
        )
        return {
            "ok": quick_check == "ok" and foreign_key_violations == 0,
            "quick_check": quick_check,
            "foreign_key_violations": foreign_key_violations,
            "counts": counts,
            "document_roots": document_roots,
            "derivations": derivations,
        }
    finally:
        connection.close()

