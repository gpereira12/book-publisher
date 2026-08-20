"""Auditorias determinísticas de contradições e cronologia."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from shared.db_engine import connect


@dataclass(frozen=True, slots=True)
class ContinuityIssue:
    code: str
    severity: str
    message: str
    evidence: dict[str, object]


def audit_book_continuity(db_path: str | Path) -> list[ContinuityIssue]:
    connection = connect(db_path, read_only=True)
    issues: list[ContinuityIssue] = []
    try:
        rows = connection.execute(
            """SELECT subject.canonical_name AS subject, predicate.code AS predicate,
                      COALESCE(object.entity_uid, claim.object_value_json) AS value,
                      continuity.code AS continuity, authority.authority_rank,
                      claim.id, scene.scene_uid, rule.cardinality,
                      rule.temporal_mode, valid_from.scene_uid AS valid_from_uid,
                      valid_to.scene_uid AS valid_to_uid,
                      from_chapter.ordinal AS from_chapter_ordinal,
                      valid_from.ordinal AS from_scene_ordinal,
                      to_chapter.ordinal AS to_chapter_ordinal,
                      valid_to.ordinal AS to_scene_ordinal,
                      asserted_chapter.ordinal AS asserted_chapter_ordinal,
                      scene.ordinal AS asserted_scene_ordinal
               FROM entity_claims AS claim
               JOIN entities AS subject ON subject.id = claim.subject_entity_id
               JOIN claim_predicates AS predicate ON predicate.id = claim.predicate_id
               LEFT JOIN entities AS object ON object.id = claim.object_entity_id
               LEFT JOIN continuity_branches AS continuity ON continuity.id = claim.continuity_id
               LEFT JOIN authority_sources AS authority ON authority.id = claim.authority_source_id
               LEFT JOIN claim_predicate_rules AS rule ON rule.predicate_id = claim.predicate_id
               LEFT JOIN scenes AS valid_from ON valid_from.id = claim.valid_from_scene_id
               LEFT JOIN chapters AS from_chapter ON from_chapter.id = valid_from.chapter_id
               LEFT JOIN scenes AS valid_to ON valid_to.id = claim.valid_to_scene_id
               LEFT JOIN chapters AS to_chapter ON to_chapter.id = valid_to.chapter_id
               JOIN scenes AS scene ON scene.id = claim.asserted_scene_id
               JOIN chapters AS asserted_chapter ON asserted_chapter.id = scene.chapter_id
               ORDER BY subject.entity_uid, predicate.code, continuity.code, claim.id"""
        ).fetchall()
        groups: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
        for row in rows:
            groups.setdefault(
                (row["subject"], row["predicate"], row["continuity"] or "main"), []
            ).append(row)
        for key, claims in groups.items():
            if (claims[0]["cardinality"] or "single") != "single":
                continue

            def interval(row: sqlite3.Row) -> tuple[tuple[int, int], tuple[int, int]]:
                mode = row["temporal_mode"] or "timeless"
                minimum = (-1, -1)
                maximum = (2**31 - 1, 2**31 - 1)
                asserted = (row["asserted_chapter_ordinal"], row["asserted_scene_ordinal"])
                if mode == "timeless":
                    return minimum, maximum
                start = (
                    (row["from_chapter_ordinal"], row["from_scene_ordinal"])
                    if row["from_chapter_ordinal"] is not None else asserted
                )
                if mode == "point":
                    return start, start
                end = (
                    (row["to_chapter_ordinal"], row["to_scene_ordinal"])
                    if row["to_chapter_ordinal"] is not None else maximum
                )
                return start, end

            conflicts: list[sqlite3.Row] = []
            for index, first in enumerate(claims):
                first_start, first_end = interval(first)
                for second in claims[index + 1:]:
                    second_start, second_end = interval(second)
                    if first["value"] != second["value"] and max(first_start, second_start) <= min(first_end, second_end):
                        conflicts.extend((first, second))
            if conflicts:
                unique_claims = {row["id"]: row for row in conflicts}
                conflicting_claims = list(unique_claims.values())
                top_rank = max((row["authority_rank"] or 0) for row in conflicting_claims)
                top_values = {
                    row["value"] for row in conflicting_claims
                    if (row["authority_rank"] or 0) == top_rank
                }
                severity = "error" if len(top_values) > 1 else "warning"
                issues.append(ContinuityIssue(
                    "conflicting_claims",
                    severity,
                    f"{key[0]} possui valores divergentes para {key[1]} em {key[2]}",
                    {
                        "claim_ids": [row["id"] for row in conflicting_claims],
                        "values": sorted({row["value"] for row in conflicting_claims}),
                    },
                ))
    finally:
        connection.close()
    return issues


def audit_universe_continuity(db_path: str | Path) -> list[ContinuityIssue]:
    connection = connect(db_path, read_only=True)
    issues: list[ContinuityIssue] = []
    try:
        conflicts = connection.execute(
            """SELECT first_claim_id, second_claim_id, explanation, status
               FROM claim_conflicts WHERE status = 'open'"""
        ).fetchall()
        for row in conflicts:
            issues.append(ContinuityIssue(
                "universe_claim_conflict", "error", row["explanation"] or "Claims incompatíveis",
                {"claim_ids": [row["first_claim_id"], row["second_claim_id"]]},
            ))
        claims = connection.execute(
            """SELECT claim.id, subject.entity_uid AS subject_uid,
                      predicate.code AS predicate,
                      COALESCE(object.entity_uid, claim.object_value_json) AS value,
                      COALESCE(continuity.code, 'main') AS continuity
               FROM universe_claims AS claim
               JOIN universe_entities AS subject ON subject.id = claim.subject_entity_id
               JOIN claim_predicates AS predicate ON predicate.id = claim.predicate_id
               LEFT JOIN universe_entities AS object ON object.id = claim.object_entity_id
               LEFT JOIN continuity_branches AS continuity ON continuity.id = claim.continuity_id"""
        ).fetchall()
        claim_groups: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
        for claim in claims:
            claim_groups.setdefault(
                (claim["subject_uid"], claim["predicate"], claim["continuity"]), []
            ).append(claim)
        for key, group in claim_groups.items():
            values = {claim["value"] for claim in group}
            if len(values) > 1:
                issues.append(ContinuityIssue(
                    "derived_universe_claim_conflict",
                    "error",
                    f"Claims divergentes para {key[0]} / {key[1]} em {key[2]}",
                    {"claim_ids": [claim["id"] for claim in group], "values": sorted(values)},
                ))
        edges = connection.execute(
            "SELECT earlier_event_id, later_event_id FROM event_precedence"
        ).fetchall()
        graph: dict[int, set[int]] = {}
        for edge in edges:
            graph.setdefault(edge[0], set()).add(edge[1])
        visiting: set[int] = set()
        visited: set[int] = set()

        def visit(node: int, trail: list[int]) -> list[int] | None:
            if node in visiting:
                return trail[trail.index(node):] + [node]
            if node in visited:
                return None
            visiting.add(node)
            trail.append(node)
            for target in graph.get(node, set()):
                cycle = visit(target, trail)
                if cycle:
                    return cycle
            trail.pop()
            visiting.remove(node)
            visited.add(node)
            return None

        for node in graph:
            cycle = visit(node, [])
            if cycle:
                issues.append(ContinuityIssue(
                    "timeline_cycle", "critical", "A cronologia contém um ciclo",
                    {"event_ids": cycle},
                ))
                break
    finally:
        connection.close()
    return issues


def issues_as_json(issues: list[ContinuityIssue]) -> str:
    return json.dumps([asdict(issue) for issue in issues], ensure_ascii=False, indent=2)
