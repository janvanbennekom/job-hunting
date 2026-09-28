"""JobHunter Streamlit dashboard entry (Phase 10)."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="JobHunter",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

home = st.Page("pages/home.py", title="Home", icon="🏠", default=True)
opportunities = st.Page("pages/opportunities.py", title="Opportunities", icon="📋")
applications = st.Page("pages/applications.py", title="Applications", icon="📨")
detail = st.Page("pages/opportunity_detail.py", title="Opportunity detail", icon="🔎")
strategy = st.Page("pages/strategy.py", title="Search strategy", icon="🎯")

pg = st.navigation([home, opportunities, applications, detail, strategy])
pg.run()
