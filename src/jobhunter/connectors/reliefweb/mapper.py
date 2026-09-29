"""Map ReliefWeb API job records to RawOpportunity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jobhunter.connectors.developmentaid.html_text import html_to_plain_text
from jobhunter.connectors.reliefweb.identity import RELIEFWEB_JOBS_ENTRY_URL
from jobhunter.domain.opportunity_structured_facts import (
    OpportunityStructuredFacts,
    build_structured_facts_mapping,
)
from jobhunter.domain.raw_opportunity import RawOpportunity


def reliefweb_job_listing_url(job_id: str) -> str:
    return f"https://reliefweb.int/job/{job_id}"


def _field_list_names(value: Any, key: str = "name") -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get(key)
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return tuple(names)


def _organisation(fields: dict[str, Any]) -> str | None:
    sources = fields.get("source")
    if isinstance(sources, list) and sources:
        first = sources[0]
        if isinstance(first, dict):
            name = first.get("name") or first.get("shortname")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


def _date_field(fields: dict[str, Any], key: str) -> str | None:
    dates = fields.get("date")
    if not isinstance(dates, dict):
        return None
    value = dates.get(key)
    if value is None:
        return None
    return str(value)


def _structured_from_fields(fields: dict[str, Any]) -> OpportunityStructuredFacts:
    contract = _field_list_names(fields.get("type"))
    contract_label = contract[0] if contract else None
    application_url = fields.get("url")
    if isinstance(application_url, str):
        application_url = application_url.strip() or None
    else:
        application_url = None
    return OpportunityStructuredFacts(
        sectors=_field_list_names(fields.get("theme")),
        languages=(),
        minimum_experience_years=None,
        organisation_type=None,
        contract_type_label=contract_label,
        application_url=application_url,
        content_last_updated=_date_field(fields, "changed"),
        salary_summary=None,
        document_refs=(),
    )


def map_reliefweb_job_to_raw(
    record: dict[str, Any],
    *,
    source_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    job_id = record.get("id")
    if job_id is None:
        raise ValueError("ReliefWeb job record is missing id")
    job_id_str = str(job_id).strip()
    fields = record.get("fields")
    if not isinstance(fields, dict):
        raise ValueError(f"ReliefWeb job {job_id_str} is missing fields")

    title = fields.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"ReliefWeb job {job_id_str} is missing title")

    listing_url = reliefweb_job_listing_url(job_id_str)
    organisation = _organisation(fields)
    countries = _field_list_names(fields.get("country"))
    location = "; ".join(countries) if countries else None

    body_html = fields.get("body")
    description = html_to_plain_text(
        body_html if isinstance(body_html, str) else None
    )
    if not description:
        description_parts = [
            f"Title: {title.strip()}",
            f"Organisation: {organisation}" if organisation else None,
            f"Location: {location}" if location else None,
            f"Closing: {_date_field(fields, 'closing')}" if _date_field(fields, "closing") else None,
        ]
        description = "\n".join(part for part in description_parts if part)

    structured = _structured_from_fields(fields)
    structured_mapping = build_structured_facts_mapping(structured)
    extra: dict[str, Any] = {
        "source_connector": "reliefweb",
        "source_listing_id": job_id_str,
        "source_posted_date": _date_field(fields, "created"),
        "career_categories": list(_field_list_names(fields.get("career_category"))),
    }
    if structured_mapping:
        extra["structured_facts"] = structured_mapping

    return RawOpportunity(
        id=f"rw-raw-{job_id_str}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=job_id_str,
        source_url=listing_url,
        retrieved_at=retrieved_at,
        raw_title=title.strip(),
        raw_organisation=organisation,
        raw_location=location,
        raw_deadline=_date_field(fields, "closing"),
        raw_description=description,
        extra=extra,
    )


def _raw_id_for_scan(scan_id: str, job_id: str) -> str:
    scan_key = scan_id.replace("-", "")[:8]
    return f"rw-{scan_key}-{job_id}"


def map_reliefweb_job_to_raw_for_scan(
    record: dict[str, Any],
    *,
    source_id: str,
    scan_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    job_id = record.get("id")
    if job_id is None:
        raise ValueError("ReliefWeb job record is missing id")
    raw = map_reliefweb_job_to_raw(
        record, source_id=source_id, retrieved_at=retrieved_at
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
