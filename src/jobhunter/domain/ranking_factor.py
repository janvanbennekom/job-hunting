"""Single explainability factor within a ranking result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jobhunter.domain.ranking_enums import FactorEffect
from jobhunter.domain.serialization import enum_to_value, prune_none


@dataclass(slots=True)
class RankingFactor:
    code: str
    effect: FactorEffect
    summary: str
    contribution: int | None = None

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "code": self.code,
                "effect": enum_to_value(self.effect),
                "summary": self.summary,
                "contribution": self.contribution,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> RankingFactor:
        from jobhunter.domain.serialization import value_to_enum

        return cls(
            code=data["code"],
            effect=value_to_enum(FactorEffect, data["effect"]),
            summary=data["summary"],
            contribution=data.get("contribution"),
        )
