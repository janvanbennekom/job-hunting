"""Load source-neutral structured facts from the latest raw observation."""

from __future__ import annotations

from sqlalchemy.orm import Session

from jobhunter.domain.opportunity_structured_facts import (
    OpportunityStructuredFacts,
    parse_structured_facts_from_extra,
)
from jobhunter.infrastructure.persistence.opportunity_processing_repositories import (
    OpportunityObservationRepository,
)
from jobhunter.infrastructure.persistence.repositories import RawOpportunityRepository


class OpportunityStructuredFactsLoader:
    def __init__(self, session: Session) -> None:
        self._observations = OpportunityObservationRepository(session)
        self._raw = RawOpportunityRepository(session)

    def load_for_opportunity(self, opportunity_id: str) -> OpportunityStructuredFacts:
        observations = self._observations.list_for_opportunity(opportunity_id)
        if not observations:
            return OpportunityStructuredFacts()
        latest = max(
            observations,
            key=lambda obs: (obs.observed_at, obs.id),
        )
        raw = self._raw.get_by_id(latest.raw_opportunity_id)
        if raw is None:
            return OpportunityStructuredFacts()
        return parse_structured_facts_from_extra(raw.extra)
