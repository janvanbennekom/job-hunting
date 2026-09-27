"""Map DevelopmentAid API records to RawOpportunity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.developmentaid.html_text import html_to_plain_text
from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_ENTRY_URL
from jobhunter.domain.raw_opportunity import RawOpportunity


def _organisation_name(item: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    if detail:
        employer = detail.get("employer")
        if isinstance(employer, str) and employer.strip():
            return employer.strip()
    org = item.get("organization")
    if isinstance(org, dict):
        name = org.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


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

    source_url = _job_view_url(job_id, slug)
    organisation = _organisation_name(list_item, detail)
    location = list_item.get("locationNames")
    if isinstance(location, str):
        location = location.strip() or None
    else:
        location = None

    deadline = list_item.get("deadline")
    posted = list_item.get("postedDate")
    job_type = list_item.get("jobType")
    experience = list_item.get("experience")

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

    extra: dict[str, Any] = {
        "developmentaid_job_id": str(job_id),
        "developmentaid_slug": slug,
        "developmentaid_job_type": job_type,
        "developmentaid_experience_years": experience,
        "developmentaid_posted_date": posted,
        "developmentaid_fully_visible": list_item.get("fullyVisible"),
        "developmentaid_publication_status": list_item.get("publicationStatus"),
        "developmentaid_highlighted": list_item.get("highlighted"),
    }
    if detail:
        extra["developmentaid_sectors"] = detail.get("sectors")
        extra["developmentaid_languages"] = detail.get("languages")
        extra["developmentaid_locations"] = detail.get("locations")
        extra["developmentaid_expected_start"] = detail.get("expectedStartingDate")
        if detail.get("minimumExperience") is not None:
            extra["developmentaid_minimum_experience"] = detail.get(
                "minimumExperience"
            )

    return RawOpportunity(
        id=f"da-raw-{job_id}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=str(job_id),
        source_url=source_url,
        retrieved_at=retrieved_at,
        raw_title=title.strip(),
        raw_organisation=organisation,
        raw_location=location,
        raw_deadline=str(deadline) if deadline else None,
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
