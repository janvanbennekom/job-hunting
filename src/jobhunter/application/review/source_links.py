"""Primary source link selection for dashboard."""

from __future__ import annotations

from jobhunter.application.review.dtos import SourceLinkView
from jobhunter.domain.job_source import JobSource
from jobhunter.domain.opportunity_source import OpportunitySource
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository


def pick_primary_source_link(
    links: list[OpportunitySource],
    sources: JobSourceRepository | dict[str, JobSource],
) -> SourceLinkView | None:
    if not links:
        return None
    primary = max(
        links,
        key=lambda link: (
            link.last_seen_at is not None,
            link.last_seen_at or link.first_seen_at,
            link.id,
        ),
    )
    if isinstance(sources, dict):
        job_source = sources.get(primary.source_id)
    else:
        job_source = sources.get_by_id(primary.source_id)
    name = job_source.name if job_source else primary.source_id
    return SourceLinkView(
        source_id=primary.source_id,
        source_name=name,
        source_url=primary.source_url,
        original_url=primary.original_url,
        source_reference=primary.source_reference,
        first_seen_at=primary.first_seen_at,
        last_seen_at=primary.last_seen_at,
    )


def build_source_link_views(
    links: list[OpportunitySource],
    sources: JobSourceRepository,
) -> list[SourceLinkView]:
    views: list[SourceLinkView] = []
    for link in sorted(
        links,
        key=lambda item: (item.last_seen_at or item.first_seen_at, item.id),
        reverse=True,
    ):
        job_source = sources.get_by_id(link.source_id)
        name = job_source.name if job_source else link.source_id
        views.append(
            SourceLinkView(
                source_id=link.source_id,
                source_name=name,
                source_url=link.source_url,
                original_url=link.original_url,
                source_reference=link.source_reference,
                first_seen_at=link.first_seen_at,
                last_seen_at=link.last_seen_at,
            )
        )
    return views
