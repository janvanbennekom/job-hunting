"""Map AfDB RSS items to RawOpportunity."""

from __future__ import annotations

import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from jobhunter.connectors.afdb.detail import AfdbDetailPage
from jobhunter.connectors.developmentaid.html_text import html_to_plain_text
from jobhunter.connectors.afdb.identity import AFDB_CONSULTANTS_ORGANISATION
from jobhunter.domain.raw_opportunity import RawOpportunity

_NODE_ID = re.compile(r"/node/(\d+)")
_SLUG_ID = re.compile(r"-(\d+)$")


def extract_afdb_node_id(item: dict[str, Any]) -> str | None:
    guid = item.get("guid")
    if isinstance(guid, str):
        match = _NODE_ID.search(guid)
        if match:
            return match.group(1)
    link = item.get("link")
    if isinstance(link, str):
        match = _SLUG_ID.search(link.rstrip("/"))
        if match:
            return match.group(1)
    return None


def _parse_pub_date(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    try:
        return parsedate_to_datetime(value.strip()).isoformat()
    except (TypeError, ValueError, IndexError):
        return value.strip()


def map_afdb_item_to_raw(
    item: dict[str, Any],
    *,
    source_id: str,
    retrieved_at: datetime,
    detail: AfdbDetailPage | None = None,
) -> RawOpportunity:
    node_id = extract_afdb_node_id(item)
    if not node_id:
        raise ValueError("AfDB feed item is missing stable node id")

    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"AfDB item {node_id} is missing title")
    title = html.unescape(title.strip())

    link = item.get("link")
    if isinstance(link, str):
        link = html.unescape(link.strip())
    else:
        link = None

    description_html = item.get("description")
    rss_text = (
        html_to_plain_text(description_html)
        if isinstance(description_html, str)
        else None
    )
    pub_date = _parse_pub_date(
        item.get("pub_date") if isinstance(item.get("pub_date"), str) else None
    )

    closing = detail.closing_date if detail else None
    enriched_body = None
    if detail:
        enriched_body = detail.body_text or detail.meta_description

    description_parts = [
        f"Title: {title}",
        f"Organisation: {AFDB_CONSULTANTS_ORGANISATION}",
        f"Closing date: {closing}" if closing else None,
        f"Published: {pub_date}" if pub_date else None,
        enriched_body or rss_text,
    ]
    description = "\n".join(part for part in description_parts if part)

    extra: dict[str, Any] = {
        "afdb_node_id": node_id,
        "afdb_pub_date": pub_date,
        "afdb_feed_description_html": description_html,
        "organisation": AFDB_CONSULTANTS_ORGANISATION,
    }
    creator = item.get("creator")
    if isinstance(creator, str) and creator.strip():
        extra["afdb_creator"] = creator.strip()
    if title.upper().startswith("EOI"):
        extra["afdb_opportunity_kind"] = "EOI"

    return RawOpportunity(
        id=f"afdb-raw-{node_id}-{int(retrieved_at.timestamp())}",
        source_id=source_id,
        source_reference=node_id,
        source_url=link,
        retrieved_at=retrieved_at,
        raw_title=title,
        raw_organisation=AFDB_CONSULTANTS_ORGANISATION,
        raw_location=None,
        raw_deadline=closing,
        raw_description=description or None,
        extra=extra,
    )


def _raw_id_for_scan(scan_id: str, node_id: str) -> str:
    scan_key = scan_id.replace("-", "")[:8]
    return f"afdb-{scan_key}-{node_id}"


def map_afdb_item_to_raw_for_scan(
    item: dict[str, Any],
    *,
    source_id: str,
    scan_id: str,
    retrieved_at: datetime,
    detail: AfdbDetailPage | None = None,
) -> RawOpportunity:
    node_id = extract_afdb_node_id(item)
    if not node_id:
        raise ValueError("AfDB feed item is missing stable node id")
    raw = map_afdb_item_to_raw(
        item,
        source_id=source_id,
        retrieved_at=retrieved_at,
        detail=detail,
    )
    return RawOpportunity(
        id=_raw_id_for_scan(scan_id, node_id),
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
