"""Map World Bank procnotices API records to RawOpportunity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jobhunter.connectors.developmentaid.html_text import html_to_plain_text
from jobhunter.connectors.worldbank.identity import WORLDBANK_PROCUREMENT_ORGANISATION
from jobhunter.domain.raw_opportunity import RawOpportunity


def worldbank_notice_detail_url(notice_id: str) -> str:
    return (
        "https://projects.worldbank.org/en/projects-operations/"
        f"procurement-detail/{notice_id}"
    )


def map_worldbank_notice_to_raw(
    record: dict[str, Any],
    *,
    source_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    notice_id = record.get("id")
    if not notice_id or not str(notice_id).strip():
        raise ValueError("World Bank notice is missing id")

    notice_id = str(notice_id).strip()
    bid_description = record.get("bid_description")
    notice_type = record.get("notice_type")
    project_name = record.get("project_name")

    title = None
    if isinstance(bid_description, str) and bid_description.strip():
        title = bid_description.strip()
    elif isinstance(notice_type, str) and notice_type.strip():
        suffix = project_name.strip() if isinstance(project_name, str) else ""
        title = f"{notice_type.strip()}: {suffix}".strip(": ")
    if not title:
        raise ValueError(f"World Bank notice {notice_id} is missing title")

    country = record.get("project_ctry_name")
    location = country.strip() if isinstance(country, str) and country.strip() else None

    submission = record.get("submission_date")
    noticedate = record.get("noticedate")
    deadline = None
    if isinstance(submission, str) and submission.strip():
        deadline = submission.strip()
    elif isinstance(noticedate, str) and noticedate.strip():
        deadline = noticedate.strip()

    notice_text = record.get("notice_text")
    plain_notice = (
        html_to_plain_text(notice_text)
        if isinstance(notice_text, str)
        else None
    )

    description_parts = [
        f"Notice type: {notice_type}" if notice_type else None,
        f"Project: {project_name}" if project_name else None,
        f"Project ID: {record.get('project_id')}" if record.get("project_id") else None,
        f"Country: {location}" if location else None,
        f"Procurement method: {record.get('procurement_method_name')}"
        if record.get("procurement_method_name")
        else None,
        f"Bid reference: {record.get('bid_reference_no')}"
        if record.get("bid_reference_no")
        else None,
        f"Notice date: {noticedate}" if noticedate else None,
        f"Submission date: {submission}" if submission else None,
        plain_notice,
    ]
    description = "\n".join(part for part in description_parts if part)

    organisation = WORLDBANK_PROCUREMENT_ORGANISATION
    if isinstance(project_name, str) and project_name.strip():
        organisation = f"{WORLDBANK_PROCUREMENT_ORGANISATION} — {project_name.strip()}"

    extra: dict[str, Any] = {
        "worldbank_notice_id": notice_id,
        "worldbank_notice_type": notice_type,
        "worldbank_notice_status": record.get("notice_status"),
        "worldbank_notice_language": record.get("notice_lang_name"),
        "worldbank_project_id": record.get("project_id"),
        "worldbank_project_name": project_name,
        "worldbank_project_country": location,
        "worldbank_bid_reference_no": record.get("bid_reference_no"),
        "worldbank_procurement_group": record.get("procurement_group"),
        "worldbank_procurement_method_code": record.get("procurement_method_code"),
        "worldbank_procurement_method_name": record.get("procurement_method_name"),
        "worldbank_noticedate": noticedate,
        "worldbank_submission_date": submission,
        "organisation": WORLDBANK_PROCUREMENT_ORGANISATION,
    }

    return RawOpportunity(
        id=f"wb-raw-{notice_id}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=notice_id,
        source_url=worldbank_notice_detail_url(notice_id),
        retrieved_at=retrieved_at,
        raw_title=title,
        raw_organisation=organisation,
        raw_location=location,
        raw_deadline=deadline,
        raw_description=description or None,
        extra=extra,
    )


def _raw_id_for_scan(scan_id: str, notice_id: str) -> str:
    scan_key = scan_id.replace("-", "")[:8]
    return f"wb-{scan_key}-{notice_id}"


def map_worldbank_notice_to_raw_for_scan(
    record: dict[str, Any],
    *,
    source_id: str,
    scan_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    notice_id = record.get("id")
    if not notice_id:
        raise ValueError("World Bank notice is missing id")
    raw = map_worldbank_notice_to_raw(
        record, source_id=source_id, retrieved_at=retrieved_at
    )
    return RawOpportunity(
        id=_raw_id_for_scan(scan_id, str(notice_id)),
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
