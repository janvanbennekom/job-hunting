"""Map DevelopmentAid API records to RawOpportunity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.developmentaid.field_extractors import (
    build_structured_facts,
    contract_type_label,
    deadline_raw,
    expected_start_raw,
    location_label,
    organisation_name,
    posted_date_raw,
)
from jobhunter.connectors.developmentaid.html_text import html_to_plain_text
from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_ENTRY_URL
from jobhunter.domain.opportunity_structured_facts import build_structured_facts_mapping
from jobhunter.domain.raw_opportunity import RawOpportunity


def _job_view_url(job_id: int | str, slug: str | None) -> str:
    if slug:
        return f"https://www.developmentaid.org/jobs/view/{job_id}/{slug}"
    return f"{DEVELOPMENTAID_JOBS_ENTRY_URL}#job-{job_id}"


def map_developmentaid_job_to_raw(
    list_item: dict[str, Any],
    *,
    source_id: str,
    retrieved_at: datetime,
    detail: dict[str, Any] | None = None,
) -> RawOpportunity:
    job_id = list_item.get("id")
    if job_id is None:
        raise ValueError("DevelopmentAid job list item is missing id")
    title = list_item.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"DevelopmentAid job {job_id} is missing title")

    slug = list_item.get("slug")
    if isinstance(slug, str):
        slug = slug.strip() or None
    else:
        slug = None
    if detail and not slug:
        detail_slug = detail.get("slug")
        if isinstance(detail_slug, str) and detail_slug.strip():
            slug = detail_slug.strip()

    source_url = _job_view_url(job_id, slug)
    organisation = organisation_name(list_item, detail)
    location = location_label(list_item, detail)
    deadline = deadline_raw(list_item, detail)
    posted = posted_date_raw(list_item, detail)
    expected_start = expected_start_raw(list_item, detail)
    job_type = contract_type_label(list_item, detail)
    structured = build_structured_facts(list_item, detail)
    experience = structured.minimum_experience_years

    description_html = None
    if detail:
        description_html = detail.get("description")
    description = html_to_plain_text(
        description_html if isinstance(description_html, str) else None
    )
    if not description:
        description_parts = [
            f"Title: {title.strip()}",
            f"Organisation: {organisation}" if organisation else None,
            f"Location: {location}" if location else None,
            f"Job type: {job_type}" if job_type else None,
            f"Posted: {posted}" if posted else None,
            f"Deadline: {deadline}" if deadline else None,
            f"Minimum experience (years): {experience}" if experience else None,
        ]
        description = "\n".join(part for part in description_parts if part)

    structured_mapping = build_structured_facts_mapping(structured)
    extra: dict[str, Any] = {
        "source_connector": "developmentaid",
        "source_listing_id": str(job_id),
        "source_listing_slug": slug,
        "source_posted_date": posted,
        "source_expected_start_date": expected_start,
        "source_publication_status": list_item.get("publicationStatus")
        or (detail.get("public") if detail else None),
        "source_fully_visible": list_item.get("fullyVisible")
        if list_item.get("fullyVisible") is not None
        else (detail.get("fullyVisible") if detail else None),
    }
    if structured_mapping:
        extra["structured_facts"] = structured_mapping

    return RawOpportunity(
        id=f"da-raw-{job_id}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=str(job_id),
        source_url=source_url,
        retrieved_at=retrieved_at,
        raw_title=title.strip(),
        raw_organisation=organisation,
        raw_location=location,
        raw_deadline=deadline,
        raw_description=description,
        extra=extra,
    )


def _raw_id_for_scan(scan_id: str, job_id: str) -> str:
    scan_key = scan_id.replace("-", "")[:8]
    return f"da-{scan_key}-{job_id}"


def map_developmentaid_job_to_raw_for_scan(
    list_item: dict[str, Any],
    *,
    source_id: str,
    scan_id: str,
    retrieved_at: datetime,
    detail: dict[str, Any] | None = None,
) -> RawOpportunity:
    job_id = list_item.get("id")
    if job_id is None:
        raise ValueError("DevelopmentAid job list item is missing id")
    raw = map_developmentaid_job_to_raw(
        list_item,
        source_id=source_id,
        retrieved_at=retrieved_at,
        detail=detail,
    )
    return RawOpportunity(
        id=_raw_id_for_scan(scan_id, str(job_id)),
        source_id=raw.source_id,
        source_reference=raw.source_reference,
        source_url=raw.source_url,
        retrieved_at=raw.retrieved_at,
        raw_title=raw.raw_title,
        raw_organisation=raw.raw_organisation,
        raw_location=raw.raw_location,
        raw_deadline=raw.raw_deadline,
        raw_description=raw.raw_description,
        extra=dict(raw.extra),
    )
