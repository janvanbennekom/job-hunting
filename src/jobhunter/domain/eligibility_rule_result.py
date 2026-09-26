"""Single rule evaluation within an eligibility decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobhunter.domain.eligibility_enums import EligibilityRuleKind, RuleTriState
from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import enum_to_value, prune_none, value_to_enum


@dataclass(slots=True)
class EligibilityRuleResult:
    decision_id: str
    rule_kind: EligibilityRuleKind
    rule_code: str
    outcome: RuleTriState
    id: str = field(default_factory=new_domain_id)
    suggests_review: bool = False
    summary: str | None = None
    evidence: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.decision_id = require_non_empty(self.decision_id, "decision_id")
        self.rule_code = require_non_empty(self.rule_code, "rule_code")

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "decision_id": self.decision_id,
                "rule_kind": enum_to_value(self.rule_kind),
                "rule_code": self.rule_code,
                "outcome": enum_to_value(self.outcome),
                "suggests_review": self.suggests_review,
                "summary": self.summary,
                "evidence": self.evidence,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> EligibilityRuleResult:
        return cls(
            id=data["id"],
            decision_id=data["decision_id"],
            rule_kind=value_to_enum(EligibilityRuleKind, data["rule_kind"]),
            rule_code=data["rule_code"],
            outcome=value_to_enum(RuleTriState, data["outcome"]),
            suggests_review=bool(data.get("suggests_review", False)),
            summary=data.get("summary"),
            evidence=data.get("evidence"),
        )
