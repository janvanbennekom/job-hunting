"""Read models for strategy conversation workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from jobhunter.domain import RevisionChangeSource
from jobhunter.domain.revision_content_bundle import RevisionContentBundle


class ProposalOutcome(StrEnum):
    PROPOSED = "PROPOSED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    UNUSABLE = "UNUSABLE"
    INVALID = "INVALID"
    NO_OP = "NO_OP"


@dataclass(frozen=True, slots=True)
class StrategyDiffLine:
    area: str
    item_key: str
    field_name: str
    current_value: str | None
    proposed_value: str | None
    explanation: str | None = None


@dataclass(slots=True)
class StrategyChangeProposal:
    proposal_id: str
    base_revision_id: str
    user_message: str
    outcome: ProposalOutcome
    summary: str
    assumptions: list[str]
    clarification_questions: list[str]
    change_summary: str
    proposed_bundle: RevisionContentBundle | None
    content_hash: str | None
    proposed_revision_id: str | None
    diff_lines: list[StrategyDiffLine] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    model_provider: str | None = None
    model_name: str | None = None
    provider_error: str | None = None
    change_source: RevisionChangeSource = RevisionChangeSource.CONVERSATION_CONFIRMED


@dataclass(frozen=True, slots=True)
class StrategyRevisionSummary:
    revision_id: str
    revision_number: int
    status: str
    created_at: str
    change_summary: str
    change_source: str
    content_hash: str
    is_current: bool


@dataclass(frozen=True, slots=True)
class ActiveStrategyView:
    owner_key: str
    strategy_id: str
    current_revision_id: str | None
    revision_number: int | None
    change_summary: str | None
    content_hash: str | None
    themes: list[dict[str, Any]]
    criteria: list[dict[str, Any]]
    exclusions: list[dict[str, Any]]
