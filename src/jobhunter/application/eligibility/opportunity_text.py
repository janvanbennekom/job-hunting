"""Build searchable text from a normalized opportunity."""

from __future__ import annotations

from jobhunter.domain.opportunity import Opportunity


def opportunity_text_corpus(opportunity: Opportunity) -> str:
    parts = [
        opportunity.title,
        opportunity.organisation,
        opportunity.location,
        opportunity.description,
        opportunity.source_status,
    ]
    return "\n".join(part for part in parts if part and str(part).strip()).lower()
