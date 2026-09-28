"""Opportunity review queue."""

from __future__ import annotations

import streamlit as st

from jobhunter.application.review import OpportunityReviewQueryService
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
    for item in items:
        rank = str(item.dynamic_rank) if item.dynamic_rank else "—"
        band = item.priority_band.value if item.priority_band else "—"
        cols = st.columns([6, 1])
        with cols[0]:
            st.markdown(
                f"**{item.title}**  \n"
                f"{rank} · {band} · {item.lifecycle_status.value} · "
                f"{item.eligibility_status.value} · {item.organisation or '—'}"
            )
        with cols[1]:
            if st.button("View", key=f"view-{item.opportunity_id}", use_container_width=True):
                navigate_to_opportunity_detail(item.opportunity_id)
