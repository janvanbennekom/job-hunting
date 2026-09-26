"""Persisted AI profile/relevance assessment for an opportunity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobhunter.domain.assessment_enums import (
    PROFILE_ASSESSMENT_SCHEMA_VERSION,
    AssessmentStatus,
)
from jobhunter.domain.identifiers import new_domain_id, require_non_empty
from jobhunter.domain.serialization import (
    deserialize_datetime,
    enum_to_value,
    prune_none,
    serialize_datetime,
    value_to_enum,
)
from jobhunter.domain.validation import require_timezone_aware


@dataclass(slots=True)
class OpportunityProfileAssessment:
    opportunity_id: str
    search_strategy_revision_id: str
    assessed_at: datetime
    status: AssessmentStatus
    input_digest: str
    opportunity_content_digest: str
    profile_evidence_digest: str
    prompt_schema_version: str
    model_provider: str
    model_name: str
    id: str = field(default_factory=new_domain_id)
    eligibility_decision_id: str | None = None
    validation_warnings: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    provider_error: str | None = None

    def __post_init__(self) -> None:
        self.id = require_non_empty(self.id, "id")
        self.opportunity_id = require_non_empty(
            self.opportunity_id, "opportunity_id"
        )
        self.search_strategy_revision_id = require_non_empty(
            self.search_strategy_revision_id, "search_strategy_revision_id"
        )
        self.assessed_at = require_timezone_aware(
            self.assessed_at, "assessed_at"
        )
        self.input_digest = require_non_empty(self.input_digest, "input_digest")
        self.opportunity_content_digest = require_non_empty(
            self.opportunity_content_digest, "opportunity_content_digest"
        )
        self.profile_evidence_digest = require_non_empty(
            self.profile_evidence_digest, "profile_evidence_digest"
        )
        self.prompt_schema_version = require_non_empty(
            self.prompt_schema_version, "prompt_schema_version"
        )
        self.model_provider = require_non_empty(
            self.model_provider, "model_provider"
        )
        self.model_name = require_non_empty(self.model_name, "model_name")

    @property
    def is_successful(self) -> bool:
        return self.status in (
            AssessmentStatus.SUCCEEDED,
            AssessmentStatus.SUCCEEDED_WITH_WARNINGS,
        )

    def to_mapping(self) -> dict[str, Any]:
        return prune_none(
            {
                "id": self.id,
                "opportunity_id": self.opportunity_id,
                "search_strategy_revision_id": self.search_strategy_revision_id,
                "eligibility_decision_id": self.eligibility_decision_id,
                "assessed_at": serialize_datetime(self.assessed_at),
                "status": enum_to_value(self.status),
                "input_digest": self.input_digest,
                "opportunity_content_digest": self.opportunity_content_digest,
                "profile_evidence_digest": self.profile_evidence_digest,
                "prompt_schema_version": self.prompt_schema_version,
                "model_provider": self.model_provider,
                "model_name": self.model_name,
                "validation_warnings": list(self.validation_warnings),
                "result": self.result,
                "provider_error": self.provider_error,
            }
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OpportunityProfileAssessment:
        warnings = data.get("validation_warnings") or []
        return cls(
            id=data["id"],
            opportunity_id=data["opportunity_id"],
            search_strategy_revision_id=data["search_strategy_revision_id"],
            eligibility_decision_id=data.get("eligibility_decision_id"),
            assessed_at=deserialize_datetime(data["assessed_at"]),
            status=value_to_enum(AssessmentStatus, data["status"]),
            input_digest=data["input_digest"],
            opportunity_content_digest=data["opportunity_content_digest"],
            profile_evidence_digest=data["profile_evidence_digest"],
            prompt_schema_version=data.get(
                "prompt_schema_version", PROFILE_ASSESSMENT_SCHEMA_VERSION
            ),
            model_provider=data["model_provider"],
            model_name=data["model_name"],
            validation_warnings=[str(w) for w in warnings],
            result=data.get("result"),
            provider_error=data.get("provider_error"),
        )
