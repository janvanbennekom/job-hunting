"""Opportunity review queue."""

from __future__ import annotations

import streamlit as st

from jobhunter.application.review import OpportunityReviewQueryService
from jobhunter.application.review.dtos import OpportunityQueueFilters
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.ranking_enums import PriorityBand
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.ui.streamlit.bootstrap import allow_fake_results, get_session_factory
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("Opportunities")
st.caption("Default: actionable lifecycle, eligible, production assessment/ranking semantics.")

include_ineligible = st.checkbox("Include ineligible / audit view", value=False)
include_non_actionable = st.checkbox("Include closed/expired lifecycle", value=False)

col1, col2, col3 = st.columns(3)
with col1:
    band_filter = st.selectbox(
        "Ranking band",
        ["(any)"] + [band.value for band in PriorityBand],
    )
with col2:
    lifecycle_filter = st.selectbox(
        "Lifecycle",
        ["(any)"] + [status.value for status in LifecycleStatus],
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
    rows = []
    for item in items:
        rank = str(item.dynamic_rank) if item.dynamic_rank else "—"
        rows.append(
            {
                "Rank": rank,
                "Band": item.priority_band.value if item.priority_band else "—",
                "Title": item.title,
                "Organisation": item.organisation or "",
                "Location": item.location or "",
                "Deadline": str(item.deadline or ""),
                "Lifecycle": item.lifecycle_status.value,
                "Eligible": item.eligibility_status.value,
                "Relevance": item.overall_relevance or "—",
                "Assessment": item.assessment_state.value,
                "Review": item.review_disposition.value
                if item.review_disposition
                else "—",
                "Source": item.source_name or "",
                "id": item.opportunity_id,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Open detail")
    selected = st.selectbox(
        "Opportunity",
        options=[row["id"] for row in rows],
        format_func=lambda oid: next(r["Title"] for r in rows if r["id"] == oid),
    )
    if st.button("View detail"):
        st.session_state["selected_opportunity_id"] = selected
        st.switch_page("pages/opportunity_detail.py")
