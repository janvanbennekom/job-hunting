"""Opportunity review queue with bulk human triage."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from jobhunter.application.display_labels import (
    label_eligibility_status,
    label_review_disposition,
)
from jobhunter.application.review import HumanReviewService, OpportunityReviewQueryService
from jobhunter.application.review.dtos import OpportunityQueueFilters
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.ranking_enums import PriorityBand
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.ui.streamlit.bootstrap import allow_fake_results, get_session_factory
from jobhunter.ui.streamlit.navigation import get_query_param, navigate_to_opportunity_detail
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("Opportunities")
st.caption("Default: actionable lifecycle, eligible, production assessment/ranking semantics.")

eligibility_qp = get_query_param("eligibility")
lifecycle_qp = get_query_param("lifecycle")
band_qp = get_query_param("ranking_band")

include_ineligible = st.checkbox(
    "Include ineligible / audit view",
    value=eligibility_qp is not None
    and eligibility_qp != EligibilityStatus.ELIGIBLE.value,
)
include_non_actionable = st.checkbox("Include closed/expired lifecycle", value=False)

band_options = ["(any)"] + [band.value for band in PriorityBand]
lifecycle_options = ["(any)"] + [status.value for status in LifecycleStatus]

col1, col2, col3 = st.columns(3)
with col1:
    band_default = band_options.index(band_qp) if band_qp in band_options else 0
    band_filter = st.selectbox("Ranking band", band_options, index=band_default)
with col2:
    lifecycle_default = (
        lifecycle_options.index(lifecycle_qp) if lifecycle_qp in lifecycle_options else 0
    )
    lifecycle_filter = st.selectbox(
        "Lifecycle", lifecycle_options, index=lifecycle_default
    )
with col3:
    review_filter = st.selectbox(
        "Human review",
        ["(any)", "Not reviewed"]
        + [disp.value for disp in ReviewDisposition],
    )

location_filter = st.text_input("Location contains", "")
source_filter = st.text_input("Source id (optional)", "")

filters = OpportunityQueueFilters(
    allow_fake=allow_fake_results(),
    include_ineligible=include_ineligible,
    include_non_actionable_lifecycle=include_non_actionable,
    ranking_band=PriorityBand(band_filter) if band_filter != "(any)" else None,
    lifecycle=LifecycleStatus(lifecycle_filter)
    if lifecycle_filter != "(any)"
    else None,
    eligibility=EligibilityStatus(eligibility_qp) if eligibility_qp else None,
    source_id=source_filter.strip() or None,
    location_contains=location_filter.strip() or None,
)

session_factory = get_session_factory()
with session_factory() as session:
    items = OpportunityReviewQueryService(session).list_queue(filters)

if review_filter == "Not reviewed":
    items = [item for item in items if item.review_disposition is None]
elif review_filter != "(any)":
    disp = ReviewDisposition(review_filter)
    items = [item for item in items if item.review_disposition is disp]

if not items:
    st.info("No opportunities match the current filters.")
else:
    id_by_row: list[str] = []
    rows = []
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
                "Review": review_label,
            }
        )

    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
        },
        disabled=[
            "Opportunity",
            "Organisation",
            "Deadline",
            "Eligibility",
            "Rank",
            "Review",
        ],
        key="opportunity_queue_editor",
    )

    selected_ids = [
        id_by_row[index]
        for index, selected in enumerate(edited["Select"].tolist())
        if selected
    ]
    selected_count = len(selected_ids)

    st.caption(
        f"{len(items)} opportunities shown · {selected_count} selected. "
        "Bulk actions append a new review record (history is preserved)."
    )

    pending = st.session_state.get("bulk_review_pending")
    if pending:
        st.warning(
            f"Confirm **{label_review_disposition(pending['disposition'])}** "
            f"for **{pending['count']}** selected opportunities. "
            "This adds a new review entry for each; existing decisions remain in history."
        )
        confirm_cols = st.columns(2)
        with confirm_cols[0]:
            if st.button("Confirm bulk review", type="primary"):
                with session_factory() as session:
                    HumanReviewService(session).append_reviews_bulk(
                        pending["opportunity_ids"],
                        ReviewDisposition(pending["disposition"]),
                        pending.get("notes"),
                    )
                    session.commit()
                st.session_state.pop("bulk_review_pending", None)
                st.success(
                    f"Recorded {pending['disposition']} for {pending['count']} opportunities."
                )
                st.rerun()
        with confirm_cols[1]:
            if st.button("Cancel bulk review"):
                st.session_state.pop("bulk_review_pending", None)
                st.rerun()
    else:
        bulk_notes = st.text_input("Bulk notes (optional)", key="bulk_review_notes")
        action_cols = st.columns(3)
        disposition_buttons = [
            (ReviewDisposition.DISMISS, "Dismiss selected"),
            (ReviewDisposition.SHORTLIST, "Shortlist selected"),
            (ReviewDisposition.INVESTIGATE, "Investigate selected"),
        ]
        for column, (disposition, label) in zip(action_cols, disposition_buttons):
            with column:
                if st.button(
                    f"{label} ({selected_count})",
                    disabled=selected_count == 0,
                    use_container_width=True,
                ):
                    st.session_state["bulk_review_pending"] = {
                        "disposition": disposition.value,
                        "count": selected_count,
                        "opportunity_ids": list(selected_ids),
                        "notes": bulk_notes.strip() or None,
                    }
                    st.rerun()

    if selected_count == 1:
        if st.button("Open selected opportunity detail"):
            navigate_to_opportunity_detail(selected_ids[0])
