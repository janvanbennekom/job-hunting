"""Helpers so integration tests do not collide with committed dev DB rows."""

from __future__ import annotations

import copy
import uuid
from typing import Any


def unique_worldbank_notice_records(
    records: list[dict[str, Any]], *, count: int = 2
) -> list[dict[str, Any]]:
    """Return deep copies with notice ids that cannot match production scans."""
    token = uuid.uuid4().hex[:10].upper()
    isolated: list[dict[str, Any]] = []
    for index, record in enumerate(records[:count]):
        row = copy.deepcopy(record)
        row["id"] = f"OP-TEST-{token}-{index}"
        isolated.append(row)
    return isolated


def unique_developmentaid_job_id() -> int:
    """Stable-length numeric id unlikely to exist in a shared dev database."""
    return 980_000_000 + (uuid.uuid4().int % 19_999_999)


def unique_ted_notice_records(
    notices: list[dict[str, Any]], *, count: int = 2
) -> list[dict[str, Any]]:
    if not notices:
        return []
    token = uuid.uuid4().hex[:8].upper()
    isolated: list[dict[str, Any]] = []
    template = notices[0]
    for index in range(count):
        row = copy.deepcopy(template)
        row["publication-number"] = f"TEST-{token}-{index}"
        isolated.append(row)
    return isolated


def unique_adb_notice_records(
    records: list[dict[str, Any]], *, count: int = 2
) -> list[dict[str, Any]]:
    """Return copies with synthetic E- notice ids for integration tests."""
    token = uuid.uuid4().hex[:6].upper()
    isolated: list[dict[str, Any]] = []
    for index, record in enumerate(records[:count]):
        row = copy.deepcopy(record)
        notice_id = f"E-9{token}{index:03d}"
        row["notice_id"] = notice_id
        title = row.get("title") or "Test notice"
        if "E-" in title:
            title = title.rsplit("(", 1)[0].rstrip() + f" ({notice_id})"
        row["title"] = title
        isolated.append(row)
    return isolated


def unique_reliefweb_job_records(
    jobs: list[dict[str, Any]], *, count: int = 2
) -> list[dict[str, Any]]:
    if not jobs:
        return []
    token = uuid.uuid4().hex[:8]
    isolated: list[dict[str, Any]] = []
    template = jobs[0]
    for index in range(count):
        row = copy.deepcopy(template)
        row["id"] = f"9{token}{index}"[:10]
        isolated.append(row)
    return isolated
