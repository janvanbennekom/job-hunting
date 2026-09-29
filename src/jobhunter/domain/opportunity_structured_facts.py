"""Source-neutral structured opportunity metadata (from raw.extra, not DB columns)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentReference:
    title: str | None
    url: str | None


@dataclass(frozen=True, slots=True)
class OpportunityStructuredFacts:
    sectors: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    expertise: tuple[str, ...] = ()
    minimum_experience_years: int | None = None
    organisation_type: str | None = None
    contract_type_label: str | None = None
    consultant_type_label: str | None = None
    project_reference: str | None = None
    duration_label: str | None = None
    application_url: str | None = None
    content_last_updated: str | None = None
    salary_summary: str | None = None
    document_refs: tuple[DocumentReference, ...] = ()

    def to_digest_mapping(self) -> dict[str, Any]:
        return {
            "sectors": list(self.sectors),
            "languages": list(self.languages),
            "expertise": list(self.expertise),
            "minimum_experience_years": self.minimum_experience_years,
            "organisation_type": self.organisation_type,
            "contract_type_label": self.contract_type_label,
            "consultant_type_label": self.consultant_type_label,
            "project_reference": self.project_reference,
            "duration_label": self.duration_label,
            "application_url": self.application_url,
            "content_last_updated": self.content_last_updated,
            "salary_summary": self.salary_summary,
            "document_refs": [
                {"title": ref.title, "url": ref.url} for ref in self.document_refs
            ],
        }

    def is_empty(self) -> bool:
        return not any(
            (
                self.sectors,
                self.languages,
                self.expertise,
                self.minimum_experience_years is not None,
                self.organisation_type,
                self.contract_type_label,
                self.consultant_type_label,
                self.project_reference,
                self.duration_label,
                self.application_url,
                self.content_last_updated,
                self.salary_summary,
                self.document_refs,
            )
        )


def _names_from_object_list(items: Any, key: str = "name") -> tuple[str, ...]:
    if not isinstance(items, list):
        return ()
    names: list[str] = []
    for item in items:
        if isinstance(item, dict):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
        elif isinstance(item, str) and item.strip():
            names.append(item.strip())
    return tuple(names)


def _document_refs_from_list(items: Any) -> tuple[DocumentReference, ...]:
    if not isinstance(items, list) or not items:
        return ()
    refs: list[DocumentReference] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("name")
        url = item.get("url") or item.get("link")
        title_s = title.strip() if isinstance(title, str) and title.strip() else None
        url_s = url.strip() if isinstance(url, str) and url.strip() else None
        if title_s or url_s:
            refs.append(DocumentReference(title=title_s, url=url_s))
    return tuple(refs)


def parse_structured_facts_from_extra(extra: dict[str, Any] | None) -> OpportunityStructuredFacts:
    if not extra:
        return OpportunityStructuredFacts()

    nested = extra.get("structured_facts")
    if isinstance(nested, dict):
        min_exp = nested.get("minimum_experience_years")
        if min_exp is not None and not isinstance(min_exp, int):
            try:
                min_exp = int(min_exp)
            except (TypeError, ValueError):
                min_exp = None
        return OpportunityStructuredFacts(
            sectors=tuple(nested.get("sectors") or ()),
            languages=tuple(nested.get("languages") or ()),
            expertise=tuple(nested.get("expertise") or ()),
            minimum_experience_years=min_exp,
            organisation_type=_optional_str(nested.get("organisation_type")),
            contract_type_label=_optional_str(nested.get("contract_type_label")),
            consultant_type_label=_optional_str(nested.get("consultant_type_label")),
            project_reference=_optional_str(nested.get("project_reference")),
            duration_label=_optional_str(nested.get("duration_label")),
            application_url=_optional_str(nested.get("application_url")),
            content_last_updated=_optional_str(nested.get("content_last_updated")),
            salary_summary=_optional_str(nested.get("salary_summary")),
            document_refs=_document_refs_from_nested(nested.get("document_refs")),
        )

    min_exp = extra.get("developmentaid_minimum_experience")
    if min_exp is None:
        min_exp = extra.get("developmentaid_experience_years")
    if min_exp is not None and not isinstance(min_exp, int):
        try:
            min_exp = int(min_exp)
        except (TypeError, ValueError):
            min_exp = None

    return OpportunityStructuredFacts(
        sectors=_names_from_object_list(extra.get("developmentaid_sectors")),
        languages=_names_from_object_list(extra.get("developmentaid_languages")),
        minimum_experience_years=min_exp,
        organisation_type=None,
        contract_type_label=_optional_str(extra.get("developmentaid_job_type")),
        application_url=None,
        content_last_updated=None,
        salary_summary=None,
        document_refs=(),
    )


def _document_refs_from_nested(items: Any) -> tuple[DocumentReference, ...]:
    if not isinstance(items, list):
        return ()
    refs: list[DocumentReference] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        refs.append(
            DocumentReference(
                title=_optional_str(item.get("title")),
                url=_optional_str(item.get("url")),
            )
        )
    return tuple(refs)


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def build_structured_facts_mapping(facts: OpportunityStructuredFacts) -> dict[str, Any]:
    if facts.is_empty():
        return {}
    payload: dict[str, Any] = {}
    if facts.sectors:
        payload["sectors"] = list(facts.sectors)
    if facts.languages:
        payload["languages"] = list(facts.languages)
    if facts.expertise:
        payload["expertise"] = list(facts.expertise)
    if facts.minimum_experience_years is not None:
        payload["minimum_experience_years"] = facts.minimum_experience_years
    if facts.organisation_type:
        payload["organisation_type"] = facts.organisation_type
    if facts.contract_type_label:
        payload["contract_type_label"] = facts.contract_type_label
    if facts.consultant_type_label:
        payload["consultant_type_label"] = facts.consultant_type_label
    if facts.project_reference:
        payload["project_reference"] = facts.project_reference
    if facts.duration_label:
        payload["duration_label"] = facts.duration_label
    if facts.application_url:
        payload["application_url"] = facts.application_url
    if facts.content_last_updated:
        payload["content_last_updated"] = facts.content_last_updated
    if facts.salary_summary:
        payload["salary_summary"] = facts.salary_summary
    if facts.document_refs:
        payload["document_refs"] = [
            {"title": ref.title, "url": ref.url} for ref in facts.document_refs
        ]
    return payload
