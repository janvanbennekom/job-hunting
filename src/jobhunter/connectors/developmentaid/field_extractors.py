"""Extract normalized values from DevelopmentAid list/detail JSON."""

from __future__ import annotations

from typing import Any

from jobhunter.domain.date_placeholders import parse_api_date
from jobhunter.domain.opportunity_structured_facts import (
    DocumentReference,
    OpportunityStructuredFacts,
    build_structured_facts_mapping,
)


def organisation_name(list_item: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    if detail:
        employer = detail.get("employer")
        if isinstance(employer, str) and employer.strip():
            return employer.strip()
        org = detail.get("organization")
        if isinstance(org, dict):
            name = org.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    org = list_item.get("organization")
    if isinstance(org, dict):
        name = org.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def organisation_type(list_item: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    for payload in (detail, list_item):
        if not isinstance(payload, dict):
            continue
        org = payload.get("organization")
        if isinstance(org, dict):
            value = org.get("organizationTypeV2Name")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def location_label(list_item: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    if detail:
        locations = detail.get("locations")
        if isinstance(locations, list) and locations:
            names: list[str] = []
            for loc in locations:
                if isinstance(loc, dict):
                    name = loc.get("name")
                    if isinstance(name, str) and name.strip():
                        names.append(name.strip())
            if names:
                return "; ".join(names)
    location = list_item.get("locationNames")
    if isinstance(location, str):
        return location.strip() or None
    return None


def contract_type_label(list_item: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    if detail:
        job_type = detail.get("type")
        if isinstance(job_type, dict):
            name = job_type.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    job_type = list_item.get("jobType")
    if isinstance(job_type, str) and job_type.strip():
        return job_type.strip()
    return None


def minimum_experience_years(
    list_item: dict[str, Any], detail: dict[str, Any] | None
) -> int | None:
    if detail and detail.get("minimumExperience") is not None:
        value = detail.get("minimumExperience")
    else:
        value = list_item.get("experience")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def posted_date_raw(list_item: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    if detail:
        posted = detail.get("postedDate")
        if posted:
            return str(posted)
    posted = list_item.get("postedDate")
    return str(posted) if posted else None


def deadline_raw(list_item: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    if detail and detail.get("deadline"):
        return str(detail.get("deadline"))
    deadline = list_item.get("deadline")
    return str(deadline) if deadline else None


def expected_start_raw(list_item: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    if detail and detail.get("expectedStartingDate"):
        return str(detail.get("expectedStartingDate"))
    value = list_item.get("expectedStartingDate")
    return str(value) if value else None


def application_url(detail: dict[str, Any] | None) -> str | None:
    if not detail:
        return None
    url = detail.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    return None


def salary_summary(detail: dict[str, Any] | None) -> str | None:
    if not detail:
        return None
    if not detail.get("hasSalary"):
        return None
    salary = detail.get("salary")
    if isinstance(salary, str) and salary.strip():
        return salary.strip()
    if salary is not None and not isinstance(salary, (dict, list)):
        return str(salary)
    return None


def content_last_updated(detail: dict[str, Any] | None) -> str | None:
    if not detail:
        return None
    updated = detail.get("lastUpdated")
    if updated is None:
        return None
    return str(updated)


def sectors_and_languages(
    detail: dict[str, Any] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not detail:
        return (), ()
    sectors: list[str] = []
    for item in detail.get("sectors") or []:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                sectors.append(name.strip())
    languages: list[str] = []
    for item in detail.get("languages") or []:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                languages.append(name.strip())
    return tuple(sectors), tuple(languages)


def document_refs(detail: dict[str, Any] | None) -> tuple[DocumentReference, ...]:
    if not detail:
        return ()
    docs = detail.get("documents")
    if not isinstance(docs, list) or not docs:
        return ()
    refs: list[DocumentReference] = []
    for item in docs:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("name")
        url = item.get("url") or item.get("link")
        title_s = title.strip() if isinstance(title, str) and title.strip() else None
        url_s = url.strip() if isinstance(url, str) and url.strip() else None
        if title_s or url_s:
            refs.append(DocumentReference(title=title_s, url=url_s))
    return tuple(refs)


def build_structured_facts(
    list_item: dict[str, Any], detail: dict[str, Any] | None
) -> OpportunityStructuredFacts:
    sectors, languages = sectors_and_languages(detail)
    facts = OpportunityStructuredFacts(
        sectors=sectors,
        languages=languages,
        minimum_experience_years=minimum_experience_years(list_item, detail),
        organisation_type=organisation_type(list_item, detail),
        contract_type_label=contract_type_label(list_item, detail),
        application_url=application_url(detail),
        content_last_updated=content_last_updated(detail),
        salary_summary=salary_summary(detail),
        document_refs=document_refs(detail),
    )
    return facts


def expected_start_date_for_normalization(
    list_item: dict[str, Any], detail: dict[str, Any] | None
):
    return parse_api_date(expected_start_raw(list_item, detail))


def posted_date_for_normalization(list_item: dict[str, Any], detail: dict[str, Any] | None):
    return parse_api_date(posted_date_raw(list_item, detail))


def deadline_date_for_normalization(list_item: dict[str, Any], detail: dict[str, Any] | None):
    return parse_api_date(deadline_raw(list_item, detail))
