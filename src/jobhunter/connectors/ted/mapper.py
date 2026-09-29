"""Map TED Search API notices to RawOpportunity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jobhunter.domain.opportunity_structured_facts import (
    OpportunityStructuredFacts,
    build_structured_facts_mapping,
)
from jobhunter.domain.raw_opportunity import RawOpportunity


def ted_notice_url(publication_number: str) -> str:
    return f"https://ted.europa.eu/en/notice/{publication_number}"


def pick_localized_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    if isinstance(value, list):
        for item in value:
            text = pick_localized_text(item)
            if text:
                return text
        return None
    if isinstance(value, dict):
        for lang in ("eng", "en", "EN", "deu", "fra"):
            if lang in value:
                text = pick_localized_text(value[lang])
                if text:
                    return text
        for nested in value.values():
            text = pick_localized_text(nested)
            if text:
                return text
    return None


def _external_link(notice: dict[str, Any]) -> str | None:
    links = notice.get("links")
    if isinstance(links, dict):
        for key in ("pdf", "html", "xml"):
            entry = links.get(key)
            if isinstance(entry, dict):
                for lang_val in entry.values():
                    if isinstance(lang_val, str) and lang_val.startswith("http"):
                        return lang_val
    return None


def map_ted_notice_to_raw(
    notice: dict[str, Any],
    *,
    source_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    publication_number = pick_localized_text(notice.get("publication-number"))
    if not publication_number:
        raise ValueError("TED notice is missing publication-number")

    title = pick_localized_text(notice.get("notice-title"))
    if not title:
        title = f"TED notice {publication_number}"

    organisation = pick_localized_text(notice.get("buyer-name"))
    location = pick_localized_text(notice.get("buyer-country"))
    deadline = pick_localized_text(notice.get("deadline-receipt-request"))
    description_lot = pick_localized_text(notice.get("description-lot"))
    notice_type = pick_localized_text(notice.get("notice-type"))

    description_parts = [
        f"Notice type: {notice_type}" if notice_type else None,
        f"Buyer: {organisation}" if organisation else None,
        f"Country: {location}" if location else None,
        f"Deadline: {deadline}" if deadline else None,
        description_lot,
    ]
    description = "\n".join(part for part in description_parts if part)

    listing_url = ted_notice_url(publication_number)
    application_url = _external_link(notice)

    structured = OpportunityStructuredFacts(
        contract_type_label=notice_type,
        application_url=application_url,
    )
    structured_mapping = build_structured_facts_mapping(structured)
    extra: dict[str, Any] = {
        "source_connector": "ted",
        "source_listing_id": publication_number,
        "ted_publication_number": publication_number,
    }
    if structured_mapping:
        extra["structured_facts"] = structured_mapping

    return RawOpportunity(
        id=f"ted-raw-{publication_number}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=publication_number,
        source_url=listing_url,
        retrieved_at=retrieved_at,
        raw_title=title,
        raw_organisation=organisation,
        raw_location=location,
        raw_deadline=deadline,
        raw_description=description or None,
        extra=extra,
    )


def _raw_id_for_scan(scan_id: str, publication_number: str) -> str:
    scan_key = scan_id.replace("-", "")[:8]
    safe = publication_number.replace("/", "-")
    return f"ted-{scan_key}-{safe}"


def map_ted_notice_to_raw_for_scan(
    notice: dict[str, Any],
    *,
    source_id: str,
    scan_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    publication_number = pick_localized_text(notice.get("publication-number"))
    if not publication_number:
        raise ValueError("TED notice is missing publication-number")
    raw = map_ted_notice_to_raw(
        notice, source_id=source_id, retrieved_at=retrieved_at
    )
    return RawOpportunity(
        id=_raw_id_for_scan(scan_id, publication_number),
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
