"""Operational source configuration overview (Phase 15)."""

from __future__ import annotations

import streamlit as st

from jobhunter.application.sources.query_service import SourceOperationalQueryService
from jobhunter.ui.streamlit.bootstrap import get_session_factory
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("Sources")
st.caption(
    "Where JobHunter looks for opportunities. Acquisition settings are read from "
    "`automation.json` (operational config — not search strategy revisions). "
    "Edit that file on the deployment host to change enabled/keyword/limit options."
)

session_factory = get_session_factory()
with session_factory() as session:
    rows = SourceOperationalQueryService(session).list_sources()

if not rows:
    st.info("No connectors registered.")
    st.stop()

table = [
    {
        "Source": row.display_name,
        "Enabled": "Yes" if row.enabled else "No",
        "Connector": row.connector_label,
        "Last scan": row.last_scan_finished_at or row.last_scan_started_at or "—",
        "Last status": row.last_scan_status or "—",
        "Opportunities": row.opportunity_link_count,
        "Processed": row.records_processed if row.records_processed is not None else "—",
        "Limit": row.limit if row.configured else "—",
        "Keyword": row.keyword or "—",
        "Fetch details": "Yes" if row.fetch_details else "No",
    }
    for row in rows
]
st.dataframe(table, use_container_width=True, hide_index=True)

for row in rows:
    if row.last_error_summary:
        st.warning(f"**{row.display_name}** — {row.last_error_summary}")
    if row.records_retrieved is not None:
        st.caption(
            f"{row.display_name}: {row.records_retrieved} retrieved, "
            f"{row.records_failed or 0} failed (latest scan)."
        )

st.markdown(
    "**Extension point:** register new connectors in "
    "`application/sources/registry.py` and `infrastructure/automation/config.py` "
    "(known source keys); add a matching `sources` entry in `automation.json`."
)
