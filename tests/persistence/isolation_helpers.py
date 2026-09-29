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
