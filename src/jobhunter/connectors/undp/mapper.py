"""Map UNDP RSS items to RawOpportunity."""

from __future__ import annotations

import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from jobhunter.connectors.developmentaid.html_text import html_to_plain_text
from jobhunter.connectors.undp.identity import UNDP_JOBS_ORGANISATION
from jobhunter.domain.raw_opportunity import RawOpportunity

_REQUISITION_ID = re.compile(r"/requisitions/job/(\d+)(?:\D|$)")
_DEADLINE = re.compile(
    r"Application\s+Deadline\s*:\s*([^<\n]+)",
    re.IGNORECASE,
)


def extract_undp_requisition_id(link: str | None) -> str | None:
    if not link:
        return None
    match = _REQUISITION_ID.search(link)
    return match.group(1) if match else None


def _parse_pub_date(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    try:
        dt = parsedate_to_datetime(value.strip())
        return dt.isoformat()
    except (TypeError, ValueError, IndexError):
        return value.strip()


def _parse_deadline(description: str | None) -> str | None:
    if not description:
        return None
    match = _DEADLINE.search(description)
    if not match:
        return None
    return html.unescape(match.group(1)).strip()


def _location_from_title(title: str) -> str | None:
    if " - " not in title:
        return None
    return title.rsplit(" - ", 1)[-1].strip() or None


def map_undp_item_to_raw(
    item: dict[str, Any],
    *,
    source_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    link = item.get("link")
    if isinstance(link, str):
        link = html.unescape(link.strip())
    else:
        link = None

    requisition_id = extract_undp_requisition_id(link)
    if not requisition_id:
        raise ValueError("UNDP feed item is missing requisition id in link")

    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"UNDP job {requisition_id} is missing title")
    title = html.unescape(title.strip())

    description_html = item.get("description")
    description_plain = (
        html_to_plain_text(description_html)
        if isinstance(description_html, str)
        else None
    )
    deadline = _parse_deadline(
        description_html if isinstance(description_html, str) else None
    )
    location = _location_from_title(title)
    pub_date = _parse_pub_date(
        item.get("pub_date") if isinstance(item.get("pub_date"), str) else None
    )

    description_parts = [
        f"Title: {title}",
        f"Organisation: {UNDP_JOBS_ORGANISATION}",
        f"Location: {location}" if location else None,
        f"Application deadline: {deadline}" if deadline else None,
        f"Published: {pub_date}" if pub_date else None,
        description_plain,
    ]
    description = "\n".join(part for part in description_parts if part)

    extra: dict[str, Any] = {
        "undp_requisition_id": requisition_id,
        "undp_pub_date": pub_date,
        "undp_feed_description_html": description_html,
        "organisation": UNDP_JOBS_ORGANISATION,
    }
    creator = item.get("creator")
    if isinstance(creator, str) and creator.strip():
        extra["undp_creator"] = creator.strip()

    return RawOpportunity(
        id=f"undp-raw-{requisition_id}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=requisition_id,
        source_url=link,
        retrieved_at=retrieved_at,
        raw_title=title,
        raw_organisation=UNDP_JOBS_ORGANISATION,
        raw_location=location,
        raw_deadline=deadline,
        raw_description=description or None,
        extra=extra,
    )


def _raw_id_for_scan(scan_id: str, requisition_id: str) -> str:
    scan_key = scan_id.replace("-", "")[:8]
    return f"undp-{scan_key}-{requisition_id}"


def map_undp_item_to_raw_for_scan(
    item: dict[str, Any],
    *,
    source_id: str,
    scan_id: str,
    retrieved_at: datetime,
) -> RawOpportunity:
    link = item.get("link")
    requisition_id = extract_undp_requisition_id(
        html.unescape(link.strip()) if isinstance(link, str) else None
    )
    if not requisition_id:
        raise ValueError("UNDP feed item is missing requisition id in link")
    raw = map_undp_item_to_raw(item, source_id=source_id, retrieved_at=retrieved_at)
    return RawOpportunity(
        id=_raw_id_for_scan(scan_id, requisition_id),
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
