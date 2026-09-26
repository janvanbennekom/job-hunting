"""Append-only deterministic ranking result for an opportunity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.ranking_enums import (
    RANKING_METHOD_VERSION,
    PriorityBand,
    RankingStatus,
)
from jobhunter.domain.ranking_factor import RankingFactor
from jobhunter.domain.serialization import (
    deserialize_datetime,
    enum_to_value,
    prune_none,
    serialize_datetime,
    value_to_enum,
)
from jobhunter.domain.validation import require_timezone_aware


@dataclass(slots=True)
class OpportunityRanking:
    opportunity_id: str
    search_strategy_revision_id: str
    ranked_at: datetime
    status: RankingStatus
    input_digest: str
    ranking_method_version: str
    ranking_config_hash: str
    id: str = field(default_factory=new_domain_id)
    eligibility_decision_id: str | None = None
    profile_assessment_id: str | None = None
    priority_band: PriorityBand | None = None
    internal_sort_score: int | None = None
    factors: list[RankingFactor] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    exclusion_reason: str | None = None
    unranked_reason: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.search_strategy_revision_id = require_non_empty(
            self.search_strategy_revision_id, "search_strategy_revision_id"
        )
        self.ranked_at = require_timezone_aware(self.ranked_at, "ranked_at")
        self.input_digest = require_non_empty(self.input_digest, "input_digest")
        self.ranking_method_version = require_non_empty(
            self.ranking_method_version, "ranking_method_version"
        )
        self.ranking_config_hash = require_non_empty(
            self.ranking_config_hash, "ranking_config_hash"
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "search_strategy_revision_id": self.search_strategy_revision_id,
                "eligibility_decision_id": self.eligibility_decision_id,
                "profile_assessment_id": self.profile_assessment_id,
                "ranked_at": serialize_datetime(self.ranked_at),
                "status": enum_to_value(self.status),
                "priority_band": (
                    enum_to_value(self.priority_band)
                    if self.priority_band is not None
                    else None
                ),
                "input_digest": self.input_digest,
                "ranking_method_version": self.ranking_method_version,
                "ranking_config_hash": self.ranking_config_hash,
                "internal_sort_score": self.internal_sort_score,
                "factors": [f.to_mapping() for f in self.factors],
                "warnings": list(self.warnings),
                "exclusion_reason": self.exclusion_reason,
                "unranked_reason": self.unranked_reason,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunityRanking:
        factors = [
            RankingFactor.from_mapping(item)
            for item in (data.get("factors") or [])
        ]
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            search_strategy_revision_id=data["search_strategy_revision_id"],
            eligibility_decision_id=data.get("eligibility_decision_id"),
            profile_assessment_id=data.get("profile_assessment_id"),
            ranked_at=deserialize_datetime(data["ranked_at"]),
            status=value_to_enum(RankingStatus, data["status"]),
            priority_band=(
                value_to_enum(PriorityBand, data["priority_band"])
                if data.get("priority_band")
                else None
            ),
            input_digest=data["input_digest"],
            ranking_method_version=data.get(
                "ranking_method_version", RANKING_METHOD_VERSION
            ),
            ranking_config_hash=data["ranking_config_hash"],
            internal_sort_score=data.get("internal_sort_score"),
            factors=factors,
            warnings=[str(w) for w in (data.get("warnings") or [])],
            exclusion_reason=data.get("exclusion_reason"),
            unranked_reason=data.get("unranked_reason"),
        )
