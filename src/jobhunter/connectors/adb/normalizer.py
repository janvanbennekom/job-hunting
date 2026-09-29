"""ADB CSRN opportunity normalizer."""

from __future__ import annotations

from datetime import datetime

from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.serialization import deserialize_optional_date

_ADB_DATE_FORMATS = (
    "%d-%b-%Y",
    "%d-%b-%Y %I:%M %p",
    "%d-%B-%Y",
)


def parse_adb_date_text(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    for fmt in _ADB_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    if " " in text:
        return parse_adb_date_text(text.split(" ", 1)[0])
    return None


class AdbCsrnOpportunityNormalizer:
    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")

        extra = raw.extra or {}
        consultant_type = extra.get("adb_consultant_type")
        opportunity_type = OpportunityType.CONSULTANCY
        if isinstance(consultant_type, str) and consultant_type.lower() == "firm":
            opportunity_type = OpportunityType.UNKNOWN

        published = None
        structured = extra.get("structured_facts")
        if isinstance(structured, dict):
            published = parse_adb_date_text(
                str(structured.get("content_last_updated") or "")
            )

        deadline = None
        if raw.raw_deadline:
            dt = parse_adb_date_text(raw.raw_deadline)
            deadline = dt.date() if dt else deserialize_optional_date(raw.raw_deadline)

        return NormalizedOpportunity(
            title=title,
            organisation=(raw.raw_organisation or "").strip() or None,
            location=(raw.raw_location or "").strip() or None,
            description=(raw.raw_description or "").strip() or None,
            publication_date=published.date() if published else None,
            deadline=deadline,
            expected_start_date=None,
            opportunity_type=opportunity_type,
            source_status=None,
        )
