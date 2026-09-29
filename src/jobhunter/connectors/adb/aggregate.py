"""Merge ADB CSRN listing rows that share one notice id (E-xxxxxx-xxx)."""

from __future__ import annotations

from typing import Any


def aggregate_notice_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    One CSRN notice id maps to one consultancy opportunity; expertise rows are merged.

    Output order follows first occurrence of each notice id in the input stream.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for record in records:
        notice_id = record.get("notice_id")
        if not isinstance(notice_id, str) or not notice_id.strip():
            continue
        if notice_id not in groups:
            order.append(notice_id)
            groups[notice_id] = []
        groups[notice_id].append(record)

    return [_merge_notice_rows(groups[notice_id]) for notice_id in order]


def _merge_notice_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            row.get("row_index")
            if isinstance(row.get("row_index"), int)
            else 0
        ),
    )
    base = dict(sorted_rows[0])
    expertise_lines = _unique_expertise_lines(sorted_rows)
    base["expertise_lines"] = expertise_lines
    if len(expertise_lines) == 1:
        base["expertise"] = expertise_lines[0]
    elif expertise_lines:
        base["expertise"] = None
    base["listing_row_count"] = len(rows)
    return base


def _unique_expertise_lines(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    collected: list[str] = []

    def _add(text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        key = cleaned.casefold()
        if key in seen:
            return
        seen.add(key)
        collected.append(cleaned)

    for row in rows:
        existing_lines = row.get("expertise_lines")
        if isinstance(existing_lines, list):
            for item in existing_lines:
                if isinstance(item, str):
                    _add(item)
        expertise = row.get("expertise")
        if isinstance(expertise, str):
            _add(expertise)
    collected.sort(key=str.casefold)
    return collected
