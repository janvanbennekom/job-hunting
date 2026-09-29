"""World Bank procurement notice normalizer for Phase 5 processing."""

from __future__ import annotations

from datetime import datetime

from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.raw_opportunity import RawOpportunity
from jobhunter.domain.serialization import deserialize_optional_date

_WB_DATE_FORMATS = (
    "%d-%b-%Y",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
)


def parse_worldbank_date_text(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    for fmt in _WB_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    parsed = deserialize_optional_date(text)
    if parsed is None:
        return None
    return datetime.combine(parsed, datetime.min.time())


class WorldBankOpportunityNormalizer:
    """Maps World Bank RawOpportunity fields into the Phase 5 normalized snapshot."""

    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        title = (raw.raw_title or "").strip()
        if not title:
            raise ValueError("raw_title is required for normalization")

        extra = raw.extra or {}
        notice_type = extra.get("worldbank_notice_type")
        opportunity_type = OpportunityType.UNKNOWN
        if isinstance(notice_type, str):
            lowered = notice_type.lower()
            if "consult" in lowered or "expression of interest" in lowered:
                opportunity_type = OpportunityType.CONSULTANCY
            elif "contract award" in lowered or "bid" in lowered:
                opportunity_type = OpportunityType.OTHER

        method = extra.get("worldbank_procurement_method_name")
        if isinstance(method, str):
            method_lower = method.lower()
            if "quality" in method_lower and "based" in method_lower:
                opportunity_type = OpportunityType.CONSULTANCY

        publication = extra.get("worldbank_noticedate")
        pub_date = None
        if publication:
            dt = parse_worldbank_date_text(str(publication))
            if dt is not None:
                pub_date = dt.date()
            else:
                pub_date = deserialize_optional_date(str(publication))

        deadline = None
        if raw.raw_deadline:
            dt = parse_worldbank_date_text(raw.raw_deadline)
            if dt is not None:
                deadline = dt.date()
            else:
                deadline = deserialize_optional_date(raw.raw_deadline)

        return NormalizedOpportunity(
            title=title,
            organisation=(raw.raw_organisation or "").strip() or None,
            location=(raw.raw_location or "").strip() or None,
            description=(raw.raw_description or "").strip() or None,
            publication_date=pub_date,
            deadline=deadline,
            expected_start_date=None,
            opportunity_type=opportunity_type,
            source_status=extra.get("worldbank_notice_status"),
        )
