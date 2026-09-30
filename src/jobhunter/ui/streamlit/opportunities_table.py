"""Opportunities queue table rows for Streamlit data_editor."""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from jobhunter.application.display_labels import (
    compact_label_overall_relevance,
    compact_label_source_data_sufficiency,
    label_eligibility_status,
    label_review_disposition,
)
from jobhunter.application.review.dtos import OpportunityQueueItem
from jobhunter.ui.streamlit.navigation import opportunity_detail_href


def build_opportunity_queue_dataframe(
    items: Sequence[OpportunityQueueItem],
) -> tuple[list[str], pd.DataFrame]:
    """Build queue dataframe and parallel opportunity id list (row index aligned)."""
    id_by_row: list[str] = []
    rows: list[dict[str, object]] = []
    for item in items:
        id_by_row.append(item.opportunity_id)
        review_label = (
            label_review_disposition(item.review_disposition.value)
            if item.review_disposition
            else "—"
        )
        rank = str(item.dynamic_rank) if item.dynamic_rank else "—"
        band = item.priority_band.value if item.priority_band else "—"
        deadline = str(item.deadline) if item.deadline else "—"
        rows.append(
            {
                "Select": False,
                "Opportunity": item.title,
                "Organisation": item.organisation or "—",
                "Deadline": deadline,
                "Eligibility": label_eligibility_status(
                    item.eligibility_status.value
                ),
                "Rank": f"{rank} ({band})",
                "Relevance": compact_label_overall_relevance(
                    item.overall_relevance,
                    assessment_state=item.assessment_state.value,
                ),
                "Sufficiency": compact_label_source_data_sufficiency(
                    item.source_data_sufficiency
                ),
                "Review": review_label,
                "View": opportunity_detail_href(item.opportunity_id),
            }
        )
    return id_by_row, pd.DataFrame(rows)
