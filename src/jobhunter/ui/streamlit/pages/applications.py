"""Applications / pursuit work queue (Phase 14)."""

from __future__ import annotations

from datetime import date

import streamlit as st

from jobhunter.application.pursuit import (
    ApplicationQueueFilters,
    ApplicationQueueQueryService,
)
from jobhunter.domain.pursuit_enums import PursuitStatus
from jobhunter.ui.streamlit.bootstrap import get_session_factory
from jobhunter.ui.streamlit.navigation import navigate_to_opportunity_detail
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("Applications")
st.caption(
    "Pursuit workflow — what you are doing after deciding to pursue an opportunity. "
    "This is separate from review triage (SHORTLIST / INVESTIGATE / DISMISS)."
)

view = st.radio(
    "Show",
    ("Active pursuits", "Completed", "Overdue next action"),
    horizontal=True,
)

filters = ApplicationQueueFilters()
if view == "Active pursuits":
    filters.active_only = True
    filters.completed_only = False
elif view == "Completed":
    filters.active_only = False
    filters.completed_only = True
else:
    filters.active_only = True
    filters.overdue_next_action = True

status_filter = st.selectbox(
    "Status filter (optional)",
    ["(any)"] + [s.value for s in PursuitStatus],
)
if status_filter != "(any)":
    filters.status = PursuitStatus(status_filter)

session_factory = get_session_factory()
with session_factory() as session:
    items = ApplicationQueueQueryService(session).list_queue(filters)

if not items:
    st.info("No applications match the current filters.")
    st.stop()

today = date.today()
for item in items:
    overdue = item.next_action_overdue
    label = f"**{item.title}** — {item.current_status.value}"
    if overdue:
        label += " · overdue next action"
    with st.expander(label, expanded=False):
        st.write(f"**Organisation:** {item.organisation or '—'}")
        st.write(f"**Source:** {item.source_name or '—'}")
        st.write(f"**Ranking band:** {item.priority_band or '—'}")
        st.write(f"**Submission deadline:** {item.submission_deadline or '—'}")
        st.write(f"**Next action:** {item.next_action or '—'}")
        if item.next_action_date:
            st.write(f"**Next action date:** {item.next_action_date}")
        if item.primary_url:
            st.link_button("Open source", item.primary_url, key=f"src-{item.opportunity_id}")
        if st.button("Open opportunity detail", key=f"detail-{item.opportunity_id}"):
            navigate_to_opportunity_detail(item.opportunity_id)
