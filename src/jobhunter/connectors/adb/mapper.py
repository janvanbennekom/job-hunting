"""Map ADB CSRN records to RawOpportunity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jobhunter.connectors.adb.identity import (
    ADB_CSRN_CMS_APPLICATION_URL,
    ADB_CSRN_ORGANISATION,
)
from jobhunter.connectors.adb.parse import listing_notice_url
from jobhunter.domain.opportunity_structured_facts import (
    OpportunityStructuredFacts,
    build_structured_facts_mapping,
)
from jobhunter.domain.raw_opportunity import RawOpportunity


def map_adb_notice_to_raw(
    record: dict[str, Any],
    *,
    source_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    notice_id = record.get("notice_id")
    if not isinstance(notice_id, str) or not notice_id.strip():
        raise ValueError("ADB CSRN record is missing notice_id")
    title = record.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"ADB CSRN notice {notice_id} is missing title")

    listing_url = record.get("listing_url")
    if not isinstance(listing_url, str) or not listing_url.strip():
        listing_url = listing_notice_url(notice_id)

    project_url = record.get("project_url")
    if isinstance(project_url, str):
        project_url = project_url.strip() or None
    else:
        project_url = None

    description_parts = [
        f"Notice ID: {notice_id}",
        f"Organisation: {ADB_CSRN_ORGANISATION}",
        f"Consultant type: {record.get('consultant_type')}"
        if record.get("consultant_type")
        else None,
        f"Country: {record.get('country_code')}" if record.get("country_code") else None,
        f"Published: {record.get('published')}" if record.get("published") else None,
        f"Deadline: {record.get('deadline')}" if record.get("deadline") else None,
        f"Duration (months): {record.get('duration_months')}"
        if record.get("duration_months")
        else None,
        f"Expertise: {record.get('expertise')}" if record.get("expertise") else None,
        f"Project: {project_url}" if project_url else None,
    ]
    description = "\n".join(part for part in description_parts if part)

    consultant_type = _optional_str(record.get("consultant_type"))
    structured = OpportunityStructuredFacts(
        contract_type_label=_infer_contract_type(title),
        application_url=ADB_CSRN_CMS_APPLICATION_URL,
        content_last_updated=_optional_str(record.get("published")),
    )
    structured_mapping = build_structured_facts_mapping(structured)

    extra: dict[str, Any] = {
        "source_connector": "adb_csrn",
        "adb_notice_id": notice_id,
        "adb_project_number": record.get("project_number"),
        "adb_project_url": project_url,
        "adb_expertise": record.get("expertise"),
        "adb_duration_months": record.get("duration_months"),
        "adb_country_code": record.get("country_code"),
        "adb_consultant_type": consultant_type,
        "organisation": ADB_CSRN_ORGANISATION,
    }
    if structured_mapping:
        extra["structured_facts"] = structured_mapping

    return RawOpportunity(
        id=f"adb-raw-{notice_id}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=notice_id,
        source_url=listing_url,
        retrieved_at=retrieved_at,
        raw_title=title.strip(),
        raw_organisation=ADB_CSRN_ORGANISATION,
        raw_location=_optional_str(record.get("country_code")),
        raw_deadline=_optional_str(record.get("deadline")),
        raw_description=description,
        extra=extra,
    )


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _infer_contract_type(title: str) -> str | None:
    upper = title.upper()
    if upper.startswith("TA-"):
        return "Technical assistance"
    if upper.startswith("GRANT"):
        return "Grant-financed"
    if "LOAN" in upper[:20]:
        return "Loan-financed"
    return None


def _raw_id_for_scan(scan_id: str, notice_id: str) -> str:
    scan_key = scan_id.replace("-", "")[:8]
    safe = notice_id.replace("/", "-")
    return f"adb-{scan_key}-{safe}"


def map_adb_notice_to_raw_for_scan(
    record: dict[str, Any],
    *,
    source_id: str,
    scan_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    raw = map_adb_notice_to_raw(
        record, source_id=source_id, retrieved_at=retrieved_at
    )
    notice_id = raw.source_reference or "unknown"
    return RawOpportunity(
        id=_raw_id_for_scan(scan_id, notice_id),
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
