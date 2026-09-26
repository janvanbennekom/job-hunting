"""Dashboard home summary."""

from __future__ import annotations

import streamlit as st

from jobhunter.application.review import DashboardSummaryService
from jobhunter.ui.streamlit.bootstrap import allow_fake_results, get_session_factory
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("JobHunter — Home")
st.caption("Decision support for opportunity discovery, assessment, and ranking.")

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

    st.subheader("Lifecycle")
    st.write(summary.by_lifecycle or {"—": 0})
    st.subheader("Eligibility")
    st.write(summary.by_eligibility or {"—": 0})

    if summary.by_ranking_band:
        st.subheader("Ranking bands (current view)")
        st.write(summary.by_ranking_band)

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
    if not summary.high_priority_preview:
        st.write(
            "No HIGH-band opportunities in the current production view. "
            "Run OpenAI assessment and ranking when ready."
        )
    else:
        for item in summary.high_priority_preview:
            st.write(
                f"#{item.dynamic_rank} **{item.title}** — {item.priority_band} "
                f"({item.overall_relevance or 'no relevance'})"
            )
