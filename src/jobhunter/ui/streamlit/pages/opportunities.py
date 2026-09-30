"""Opportunity review queue with bulk human triage."""

from __future__ import annotations

import streamlit as st

from jobhunter.application.display_labels import label_review_disposition
from jobhunter.application.review import HumanReviewService, OpportunityReviewQueryService
from jobhunter.application.review.dtos import OpportunityQueueFilters
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.ranking_enums import PriorityBand
from jobhunter.domain.relevance_queue_enums import RelevanceQueueView
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.ui.streamlit.bootstrap import allow_fake_results, get_session_factory
from jobhunter.ui.streamlit.navigation import get_query_param
from jobhunter.ui.streamlit.opportunities_bulk import (
    clear_opportunity_queue_selection,
    opportunity_queue_editor_key,
    pop_bulk_review_flash,
    set_bulk_review_success_flash,
)
from jobhunter.ui.streamlit.opportunities_table import build_opportunity_queue_dataframe
from jobhunter.ui.streamlit.sidebar import render_sidebar

_RELEVANCE_QP = "relevance_queue"
_RELEVANCE_LABELS = {
    RelevanceQueueView.PRIMARY: "Primary",
    RelevanceQueueView.WEAK: "Weak fit",
    RelevanceQueueView.OUT_OF_SCOPE: "Out of scope",
    RelevanceQueueView.NEEDS_REVIEW: "Needs review",
}


def _parse_relevance_view(raw: str | None) -> RelevanceQueueView:
    if not raw:
        return RelevanceQueueView.PRIMARY
    try:
        return RelevanceQueueView(raw.strip().lower())
    except ValueError:
        return RelevanceQueueView.PRIMARY


def _default_hide_dismissed(view: RelevanceQueueView) -> bool:
    if view is RelevanceQueueView.OUT_OF_SCOPE:
        return False
    return True


render_sidebar()

st.title("Opportunities")
st.caption(
    "Default: Primary relevance (strong + moderate fit), actionable lifecycle, "
    "eligible, production assessment/ranking semantics."
)

_bulk_flash = pop_bulk_review_flash(st.session_state)
if _bulk_flash:
    st.success(_bulk_flash)

eligibility_qp = get_query_param("eligibility")
lifecycle_qp = get_query_param("lifecycle")
band_qp = get_query_param("ranking_band")
relevance_qp = get_query_param(_RELEVANCE_QP)

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

base_filters = OpportunityQueueFilters(
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
    segment_counts = OpportunityReviewQueryService(session).count_relevance_segments(
        base_filters
    )

relevance_view = _parse_relevance_view(relevance_qp)
needs_count = segment_counts.get(RelevanceQueueView.NEEDS_REVIEW.value, 0)

segment_options: list[RelevanceQueueView] = [
    RelevanceQueueView.PRIMARY,
    RelevanceQueueView.WEAK,
    RelevanceQueueView.OUT_OF_SCOPE,
]
if needs_count > 0:
    segment_options.append(RelevanceQueueView.NEEDS_REVIEW)

if relevance_view not in segment_options:
    relevance_view = RelevanceQueueView.PRIMARY

def _segment_label(view: RelevanceQueueView) -> str:
    count = segment_counts.get(view.value, 0)
    return f"{_RELEVANCE_LABELS[view]} ({count})"


picked_view = st.radio(
    "Relevance queue",
    options=segment_options,
    format_func=_segment_label,
    index=segment_options.index(relevance_view),
    horizontal=True,
)
if picked_view != relevance_view:
    st.query_params[_RELEVANCE_QP] = picked_view.value
    st.rerun()

hide_default = _default_hide_dismissed(relevance_view)
hide_dismissed = st.checkbox(
    "Hide dismissed",
    value=hide_default,
    help="Hides opportunities whose latest human review is Dismiss. "
    "Review history is unchanged.",
)

filters = OpportunityQueueFilters(
    allow_fake=base_filters.allow_fake,
    include_ineligible=base_filters.include_ineligible,
    include_non_actionable_lifecycle=base_filters.include_non_actionable_lifecycle,
    ranking_band=base_filters.ranking_band,
    lifecycle=base_filters.lifecycle,
    eligibility=base_filters.eligibility,
    source_id=base_filters.source_id,
    location_contains=base_filters.location_contains,
    relevance_queue=relevance_view,
    hide_dismissed=hide_dismissed,
)

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
    id_by_row, df = build_opportunity_queue_dataframe(items)
    edited = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "View": st.column_config.LinkColumn("View", display_text="View"),
        },
        disabled=[
            "Opportunity",
            "Organisation",
            "Deadline",
            "Eligibility",
            "Rank",
            "Relevance",
            "Sufficiency",
            "Review",
        ],
        key=opportunity_queue_editor_key(st.session_state),
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
                try:
                    with session_factory() as session:
                        HumanReviewService(session).append_reviews_bulk(
                            pending["opportunity_ids"],
                            ReviewDisposition(pending["disposition"]),
                            pending.get("notes"),
                        )
                        session.commit()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Bulk review could not be saved. Your selection is unchanged.")
                else:
                    disposition = pending["disposition"]
                    count = pending["count"]
                    st.session_state.pop("bulk_review_pending", None)
                    set_bulk_review_success_flash(
                        st.session_state,
                        f"Recorded {disposition} for {count} opportunities.",
                    )
                    clear_opportunity_queue_selection(st.session_state)
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
