"""Dashboard home summary."""

from __future__ import annotations

import streamlit as st

from jobhunter.application.review import DashboardSummaryService
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.ranking_enums import PriorityBand
from jobhunter.domain.relevance_queue_enums import RelevanceQueueView
from jobhunter.ui.streamlit.bootstrap import allow_fake_results, get_session_factory
from jobhunter.ui.streamlit.navigation import navigate_to_opportunity_detail, navigate_to_opportunities
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("JobHunter — Home")
st.caption("Decision support for opportunity discovery, assessment, and ranking.")


def _label_lifecycle(code: str) -> str:
    try:
        return LifecycleStatus(code).name.replace("_", " ").title()
    except ValueError:
        return code


def _label_eligibility(code: str) -> str:
    try:
        return EligibilityStatus(code).name.replace("_", " ").title()
    except ValueError:
        return code


def _label_band(code: str) -> str:
    try:
        return PriorityBand(code).value
    except ValueError:
        return code


def _render_count_section(
    title: str,
    counts: dict[str, int],
    label_fn,
    query_key: str,
) -> None:
    st.subheader(title)
    if not counts:
        st.write("No data yet.")
        return
    rows = [
        {"Status": label_fn(status), "Opportunities": count}
        for status, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    cols = st.columns(min(4, len(rows)) or 1)
    for index, (status, count) in enumerate(
        sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ):
        with cols[index % len(cols)]:
            if st.button(
                f"{label_fn(status)} ({count})",
                key=f"{title}-{status}",
                use_container_width=True,
            ):
                navigate_to_opportunities(**{query_key: status})


session_factory = get_session_factory()
with session_factory() as session:
    summary = DashboardSummaryService(session).build_summary(
        allow_fake=allow_fake_results()
    )

if summary.total_opportunities == 0:
    st.info("No opportunities in the database yet. Run a source scan to ingest data.")
else:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Opportunities", summary.total_opportunities)
    col2.metric("Actionable (eligible)", summary.actionable_count)
    col3.metric("Production assessed", summary.production_assessed_count)
    col4.metric("Production ranked", summary.production_ranked_count)

    _render_count_section(
        "Lifecycle",
        summary.by_lifecycle,
        _label_lifecycle,
        "lifecycle",
    )
    _render_count_section(
        "Eligibility",
        summary.by_eligibility,
        _label_eligibility,
        "eligibility",
    )

    if summary.by_ranking_band:
        _render_count_section(
            "Ranking bands (current view)",
            summary.by_ranking_band,
            _label_band,
            "ranking_band",
        )

    if summary.by_relevance_queue:
        st.subheader("Relevance queues (actionable, eligible)")
        st.caption(
            "Counts use current production assessment overall_relevance. "
            "Ranking band is independent (LOW is not a relevance gate)."
        )
        rel_labels = {
            RelevanceQueueView.PRIMARY.value: "Primary (strong + moderate)",
            RelevanceQueueView.WEAK.value: "Weak fit",
            RelevanceQueueView.OUT_OF_SCOPE.value: "Out of scope",
        }
        rel_rows = [
            {
                "Queue": rel_labels.get(key, key),
                "Opportunities": count,
            }
            for key, count in summary.by_relevance_queue.items()
        ]
        st.dataframe(rel_rows, use_container_width=True, hide_index=True)
        rel_cols = st.columns(3)
        for index, (key, count) in enumerate(summary.by_relevance_queue.items()):
            with rel_cols[index % len(rel_cols)]:
                if st.button(
                    f"{rel_labels.get(key, key)} ({count})",
                    key=f"relevance-{key}",
                    use_container_width=True,
                ):
                    navigate_to_opportunities(relevance_queue=key)

    st.subheader("Latest source scan")
    scan = summary.latest_scan
    if scan is None or scan.scan_id is None:
        st.write("No scan recorded for the default FAO source.")
    else:
        st.write(
            f"**{scan.source_name}** — {scan.status} "
            f"({scan.records_retrieved} retrieved, {scan.records_failed} failed)"
        )
        if scan.error_summary:
            st.warning(scan.error_summary)

    st.subheader("High-priority preview (HIGH band)")
    st.caption(
        "Preview is filtered by ranking band only, not by relevance queue. "
        "Use Opportunities → Primary for relevance-aware triage."
    )
    if not summary.high_priority_preview:
        st.write(
            "No HIGH-band opportunities in the current production view. "
            "Run OpenAI assessment and ranking when ready."
        )
    else:
        for item in summary.high_priority_preview:
            cols = st.columns([5, 1])
            with cols[0]:
                st.write(
                    f"#{item.dynamic_rank} **{item.title}** — {item.priority_band} "
                    f"({item.overall_relevance or 'no relevance'})"
                )
            with cols[1]:
                if st.button("Open", key=f"high-{item.opportunity_id}"):
                    navigate_to_opportunity_detail(item.opportunity_id)
