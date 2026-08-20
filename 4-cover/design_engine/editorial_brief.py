"""Brief editorial estruturado: separa estratégia do livro de decisões gráficas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple


def _tuple(value: Any) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    return tuple(str(item).strip() for item in value if str(item).strip())


@dataclass(frozen=True)
class EditorialBrief:
    title: str
    subtitle: str
    author: str
    genre: str
    audience: str
    synopsis: str
    central_promise: str
    primary_emotion: str
    visual_audience: str
    key_symbols: Tuple[str, ...]
    forbidden_elements: Tuple[str, ...]
    reference_covers: Tuple[str, ...]
    shelf_difference: str

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "EditorialBrief":
        return cls(
            title=str(config.get("titulo", "")).strip(),
            subtitle=str(config.get("subtitulo", "")).strip(),
            author=str(config.get("autor", "")).strip(),
            genre=str(config.get("genero", "")).strip(),
            audience=str(config.get("faixa_etaria", config.get("publico", ""))).strip(),
            synopsis=str(config.get("sinopse", "")).strip(),
            central_promise=str(config.get("promessa_central", "")).strip(),
            primary_emotion=str(config.get("emocao_primaria", "")).strip(),
            visual_audience=str(config.get("publico_visual", "")).strip(),
            key_symbols=_tuple(config.get("simbolos_chave")),
            forbidden_elements=_tuple(config.get("elementos_proibidos")),
            reference_covers=_tuple(config.get("capas_referencia")),
            shelf_difference=str(config.get("diferencial_de_prateleira", "")).strip(),
        )

    def audit(self) -> Dict[str, Any]:
        strategic = {
            "sinopse": self.synopsis,
            "promessa_central": self.central_promise,
            "emocao_primaria": self.primary_emotion,
            "publico_visual": self.visual_audience,
            "simbolos_chave": self.key_symbols,
            "elementos_proibidos": self.forbidden_elements,
            "diferencial_de_prateleira": self.shelf_difference,
        }
        missing = [name for name, value in strategic.items() if not value]
        completed = len(strategic) - len(missing)
        return {
            "score": round(100 * completed / len(strategic)),
            "missing": missing,
            "ready_for_art_direction": not missing,
        }

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["audit"] = self.audit()
        return data

