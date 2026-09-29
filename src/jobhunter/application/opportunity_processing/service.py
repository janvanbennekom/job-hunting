"""Source-independent opportunity processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from jobhunter.application.opportunity_processing.normalizer import (
    OpportunityNormalizer,
)
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_identity import compute_canonical_identity_key
from jobhunter.domain.opportunity_lifecycle import resolve_lifecycle_status
from jobhunter.domain.opportunity_material_changes import (
    build_change_records,
    detect_material_changes,
)
from jobhunter.domain.opportunity_change import OpportunityChange
from jobhunter.domain.opportunity_observation import OpportunityObservation
from jobhunter.domain.opportunity_source import OpportunitySource
from jobhunter.domain.opportunity_structured_facts import parse_structured_facts_from_extra
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.infrastructure.persistence.opportunity_processing_repositories import (
    OpportunityChangeRepository,
    OpportunityObservationRepository,
)
from jobhunter.infrastructure.persistence.repositories import (
    OpportunityRepository,
    OpportunitySourceRepository,
    RawOpportunityRepository,
)


@dataclass(slots=True)
class OpportunityProcessingResult:
    opportunity: Opportunity
    observation: OpportunityObservation
    changes: list[OpportunityChange]
    created_opportunity: bool


class OpportunityProcessingService:
    """Normalize, identify, deduplicate, detect changes, and persist."""

    def __init__(
        self,
        session: Session,
        normalizer: OpportunityNormalizer,
    ) -> None:
        self._session = session
        self._normalizer = normalizer
        self._raw_repo = RawOpportunityRepository(session)
        self._opportunity_repo = OpportunityRepository(session)
        self._source_link_repo = OpportunitySourceRepository(session)
        self._observation_repo = OpportunityObservationRepository(session)
        self._change_repo = OpportunityChangeRepository(session)

    def process(
        self,
        raw: RawOpportunity,
        *,
        as_of: date | None = None,
    ) -> OpportunityProcessingResult:
        existing_observation = self._observation_repo.get_by_raw_opportunity_id(
            raw.id
        )
        if existing_observation is not None:
            opportunity = self._opportunity_repo.get_by_id(
                existing_observation.opportunity_id
            )
            if opportunity is None:
                raise RuntimeError(
                    f"Observation {existing_observation.id} references "
                    f"missing opportunity {existing_observation.opportunity_id}"
                )
            changes = self._change_repo.list_for_observation(
                existing_observation.id
            )
            return OpportunityProcessingResult(
                opportunity=opportunity,
                observation=existing_observation,
                changes=changes,
                created_opportunity=False,
            )

        persisted_raw = self._raw_repo.get_by_id(raw.id)
        if persisted_raw is None:
            persisted_raw = self._raw_repo.save(raw)

        normalized = self._normalizer.normalize(persisted_raw)
        identity_key = compute_canonical_identity_key(
            persisted_raw.source_id, persisted_raw
        )
        observed_at = persisted_raw.retrieved_at
        processing_date = as_of or observed_at.date()

        existing = (
            self._opportunity_repo.get_by_canonical_identity_key(identity_key)
            if identity_key
            else None
        )
        created = existing is None

        if created:
            opportunity = self._new_opportunity(
                normalized, identity_key, processing_date
            )
            deltas = []
        else:
            deltas = detect_material_changes(existing, normalized)
            opportunity = self._apply_normalized(
                existing, normalized, identity_key, processing_date, bool(deltas)
            )

        opportunity = self._opportunity_repo.save(opportunity)
        self._upsert_source_link(
            opportunity.id,
            persisted_raw,
            observed_at,
        )

        lifecycle = opportunity.lifecycle_status
        observation = self._observation_repo.save(
            OpportunityObservation(
                opportunity_id=opportunity.id,
                raw_opportunity_id=persisted_raw.id,
                observed_at=observed_at,
                lifecycle_status=lifecycle,
            )
        )

        change_entities = build_change_records(
            opportunity.id,
            observation.id,
            observed_at,
            deltas,
        )
        saved_changes = [
            self._change_repo.save(change) for change in change_entities
        ]

        return OpportunityProcessingResult(
            opportunity=opportunity,
            observation=observation,
            changes=saved_changes,
            created_opportunity=created,
        )

    def _new_opportunity(
        self,
        normalized: NormalizedOpportunity,
        identity_key: str | None,
        as_of: date,
    ) -> Opportunity:
        lifecycle = resolve_lifecycle_status(
            is_new_opportunity=True,
            has_material_changes=False,
            normalized=normalized,
            as_of=as_of,
        )
        return Opportunity(
            title=normalized.title,
            organisation=normalized.organisation,
            location=normalized.location,
            description=normalized.description,
            publication_date=normalized.publication_date,
            deadline=normalized.deadline,
            expected_start_date=normalized.expected_start_date,
            opportunity_type=normalized.opportunity_type,
            lifecycle_status=lifecycle,
            eligibility_status=EligibilityStatus.UNKNOWN,
            canonical_identity_key=identity_key,
            source_status=normalized.source_status,
        )

    def _apply_normalized(
        self,
        existing: Opportunity,
        normalized: NormalizedOpportunity,
        identity_key: str | None,
        as_of: date,
        has_material_changes: bool,
    ) -> Opportunity:
        lifecycle = resolve_lifecycle_status(
            is_new_opportunity=False,
            has_material_changes=has_material_changes,
            normalized=normalized,
            as_of=as_of,
        )
        return Opportunity(
            id=existing.id,
            title=normalized.title,
            organisation=normalized.organisation,
            location=normalized.location,
            description=normalized.description,
            publication_date=normalized.publication_date,
            deadline=normalized.deadline,
            expected_start_date=normalized.expected_start_date,
            opportunity_type=normalized.opportunity_type,
            lifecycle_status=lifecycle,
            eligibility_status=existing.eligibility_status,
            canonical_identity_key=identity_key or existing.canonical_identity_key,
            source_status=normalized.source_status,
        )

    def _upsert_source_link(
        self,
        opportunity_id: str,
        raw: RawOpportunity,
        observed_at: datetime,
    ) -> None:
        links = self._source_link_repo.list_for_opportunity(opportunity_id)
        existing = next(
            (link for link in links if link.source_id == raw.source_id),
            None,
        )
        structured = parse_structured_facts_from_extra(raw.extra)
        application_url = structured.application_url
        listing_url = raw.source_url
        original_url = application_url if application_url else None

        if existing is None:
            self._source_link_repo.save(
                OpportunitySource(
                    opportunity_id=opportunity_id,
                    source_id=raw.source_id,
                    source_reference=raw.source_reference,
                    source_url=listing_url,
                    original_url=original_url,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                )
            )
            return

        updated = OpportunitySource(
            id=existing.id,
            opportunity_id=existing.opportunity_id,
            source_id=existing.source_id,
            source_reference=raw.source_reference or existing.source_reference,
            source_url=listing_url or existing.source_url,
            original_url=original_url or existing.original_url,
            first_seen_at=existing.first_seen_at or observed_at,
            last_seen_at=observed_at,
        )
        self._source_link_repo.save(updated)
