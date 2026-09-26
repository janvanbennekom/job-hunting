"""Infer opportunity source-data sufficiency for assessment."""

from __future__ import annotations

from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID
from jobhunter.domain.assessment_enums import SourceDataSufficiency
from jobhunter.domain.opportunity import Opportunity


def infer_source_data_sufficiency(
    opportunity: Opportunity,
    *,
    primary_source_id: str | None = None,
) -> SourceDataSufficiency:
    if primary_source_id == FAO_JOBS_SOURCE_ID:
        return SourceDataSufficiency.LIST_SUMMARY_ONLY

    description = (opportunity.description or "").strip()
    if not description:
        return SourceDataSufficiency.LIST_SUMMARY_ONLY

    if description.startswith("Title:") and "Opportunity category:" in description:
        return SourceDataSufficiency.LIST_SUMMARY_ONLY

    if len(description) < 400:
        return SourceDataSufficiency.PARTIAL

    return SourceDataSufficiency.ADEQUATE
