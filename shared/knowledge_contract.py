"""Contrato versionado e validação estrutural do conhecimento editorial YAML."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final


KNOWLEDGE_SCHEMA_VERSION: Final = 1
ENTITY_TYPES: Final = {"character", "location", "organization", "object", "concept"}
VALUE_KINDS: Final = {"any", "text", "number", "boolean", "entity", "date"}


@dataclass(frozen=True, slots=True)
class ContractIssue:
    path: str
    message: str


class KnowledgeContractError(ValueError):
    def __init__(self, issues: list[ContractIssue]) -> None:
        self.issues = issues
        super().__init__("; ".join(f"{issue.path}: {issue.message}" for issue in issues))


def validate_knowledge_payload(payload: dict[str, Any]) -> None:
    """Valida v1; dossiês legados sem ``schema_version`` continuam aceitos."""

    issues: list[ContractIssue] = []
    version = payload.get("schema_version")
    if version is not None and version != KNOWLEDGE_SCHEMA_VERSION:
        issues.append(ContractIssue("schema_version", f"esperado {KNOWLEDGE_SCHEMA_VERSION}"))
    if version is None and "entities" not in payload:
        # Compatibilidade controlada com os dossiês portugueses existentes.
        if "personagens" not in payload:
            issues.append(ContractIssue("$", "inclua schema_version/entities ou personagens"))
        if issues:
            raise KnowledgeContractError(issues)
        return

    entities = payload.get("entities", [])
    if not isinstance(entities, list):
        issues.append(ContractIssue("entities", "deve ser uma lista"))
        entities = []
    names: set[str] = set()
    for index, entity in enumerate(entities):
        path = f"entities[{index}]"
        if not isinstance(entity, dict):
            issues.append(ContractIssue(path, "deve ser um mapa"))
            continue
        name = entity.get("name")
        if not isinstance(name, str) or not name.strip():
            issues.append(ContractIssue(f"{path}.name", "texto obrigatório"))
        else:
            folded = name.casefold()
            if folded in names:
                issues.append(ContractIssue(f"{path}.name", "nome duplicado no arquivo"))
            names.add(folded)
        if entity.get("type", "concept") not in ENTITY_TYPES:
            issues.append(ContractIssue(f"{path}.type", "tipo de entidade desconhecido"))
        aliases = entity.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
            issues.append(ContractIssue(f"{path}.aliases", "deve ser uma lista de textos"))
        if entity.get("attributes") and not entity.get("state_scene_uid"):
            issues.append(ContractIssue(
                f"{path}.state_scene_uid", "obrigatório quando attributes está presente"
            ))

    predicates = payload.get("predicates", [])
    if not isinstance(predicates, list):
        issues.append(ContractIssue("predicates", "deve ser uma lista"))
        predicates = []
    for index, predicate in enumerate(predicates):
        path = f"predicates[{index}]"
        if not isinstance(predicate, dict) or not predicate.get("code"):
            issues.append(ContractIssue(path, "code é obrigatório"))
            continue
        if predicate.get("value_kind", "any") not in VALUE_KINDS:
            issues.append(ContractIssue(f"{path}.value_kind", "tipo de valor desconhecido"))
        if predicate.get("cardinality", "multiple") not in {"single", "multiple"}:
            issues.append(ContractIssue(f"{path}.cardinality", "use single ou multiple"))
        if predicate.get("temporal_mode", "timeless") not in {"timeless", "point", "interval"}:
            issues.append(ContractIssue(f"{path}.temporal_mode", "modo temporal desconhecido"))

    for collection, required in (
        ("relationships", ("source", "target")),
        ("claims", ("subject", "predicate", "scene_uid")),
    ):
        rows = payload.get(collection, [])
        if not isinstance(rows, list):
            issues.append(ContractIssue(collection, "deve ser uma lista"))
            continue
        for index, row in enumerate(rows):
            path = f"{collection}[{index}]"
            if not isinstance(row, dict):
                issues.append(ContractIssue(path, "deve ser um mapa"))
                continue
            for field in required:
                if not row.get(field):
                    issues.append(ContractIssue(f"{path}.{field}", "campo obrigatório"))
            if collection == "claims":
                has_entity = row.get("object_entity") is not None
                has_value = "value" in row
                if has_entity == has_value:
                    issues.append(ContractIssue(path, "informe exatamente object_entity ou value"))
                if row.get("valid_to_scene_uid") and not row.get("valid_from_scene_uid"):
                    issues.append(ContractIssue(
                        f"{path}.valid_from_scene_uid", "obrigatório quando valid_to_scene_uid existe"
                    ))
    if issues:
        raise KnowledgeContractError(issues)

