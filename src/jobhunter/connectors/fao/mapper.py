"""Map FAO search API records to RawOpportunity."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.fao.identity import FAO_JOBS_PORTAL_CODE
from jobhunter.domain.raw_opportunity import RawOpportunity


def _column_value(columns: list[Any], index: int) -> str | None:
    if index < 0 or index >= len(columns):
        return None
    value = columns[index]
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_locations(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [raw]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def map_fao_requisition_to_raw(
    record: dict[str, Any],
    *,
    source_id: str,
    retrieved_at: datetime,
    lang: str = "en",
) -> RawOpportunity:
    job_id = record.get("jobId")
    if not job_id:
        raise ValueError("FAO requisition is missing jobId")

    contest_no = record.get("contestNo")
    columns = list(record.get("column") or [])
    title = _column_value(columns, 0)
    if not title:
        raise ValueError(f"FAO job {job_id} is missing title")

    opportunity_category = _column_value(columns, 2)
    job_field = _column_value(columns, 3)
    location_raw = _column_value(columns, 4)
    locations = _parse_locations(location_raw)
    publication_date = _column_value(columns, 5)
    closing_date = _column_value(columns, 6)

    source_url = (
        "https://jobs.fao.org/careersection/"
        f"{FAO_JOBS_PORTAL_CODE}/jobdetail.ftl?job={job_id}&lang={lang}"
    )

    description_parts = [
        f"Title: {title}",
        f"Contest number: {contest_no}" if contest_no else None,
        f"Opportunity category: {opportunity_category}"
        if opportunity_category
        else None,
        f"Job field: {job_field}" if job_field else None,
        f"Locations: {', '.join(locations)}" if locations else None,
        f"Publication date: {publication_date}" if publication_date else None,
        f"Closing date: {closing_date}" if closing_date else None,
    ]
    description = "\n".join(part for part in description_parts if part)

    extra: dict[str, Any] = {
        "fao_job_id": str(job_id),
        "fao_contest_no": contest_no,
        "fao_opportunity_category": opportunity_category,
        "fao_job_field": job_field,
        "fao_locations": locations,
        "fao_publication_date": publication_date,
        "fao_column": columns,
        "organisation": "Food and Agriculture Organization (FAO)",
    }
    if job_field:
        extra["opportunity_type"] = "CONSULTANCY"
    if record.get("hotJob"):
        extra["fao_hot_job"] = True

    source_reference = str(contest_no) if contest_no else str(job_id)

    return RawOpportunity(
        id=f"fao-raw-{job_id}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=source_reference,
        source_url=source_url,
        retrieved_at=retrieved_at,
        raw_title=title,
        raw_organisation="Food and Agriculture Organization (FAO)",
        raw_location=locations[0] if locations else location_raw,
        raw_deadline=closing_date,
        raw_description=description,
        extra=extra,
    )


def _raw_id_for_scan(scan_id: str, job_id: str) -> str:
    scan_key = scan_id.replace("-", "")[:8]
    return f"fao-{scan_key}-{job_id}"


def map_fao_requisition_to_raw_for_scan(
    record: dict[str, Any],
    *,
    source_id: str,
    scan_id: str,
    retrieved_at: datetime,
    lang: str = "en",
) -> RawOpportunity:
    """Stable raw id per scan + job for append-only provenance."""
    job_id = record.get("jobId")
    if not job_id:
        raise ValueError("FAO requisition is missing jobId")
    raw = map_fao_requisition_to_raw(
        record,
        source_id=source_id,
        retrieved_at=retrieved_at,
        lang=lang,
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
