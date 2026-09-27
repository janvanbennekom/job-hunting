"""Shared outcome tracking for per-source scan runs."""

from __future__ import annotations

from dataclasses import dataclass, field

from jobhunter.application.opportunity_processing import OpportunityProcessingResult


@dataclass(slots=True)
class SourceScanOutcomeIds:
    processed_opportunity_ids: list[str] = field(default_factory=list)
    new_opportunity_ids: list[str] = field(default_factory=list)
    materially_updated_opportunity_ids: list[str] = field(default_factory=list)

    def record(self, result: OpportunityProcessingResult) -> None:
        opp_id = result.opportunity.id
        self.processed_opportunity_ids.append(opp_id)
        if result.created_opportunity:
            self.new_opportunity_ids.append(opp_id)
        elif result.changes:
            self.materially_updated_opportunity_ids.append(opp_id)
