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
detail = st.Page("pages/opportunity_detail.py", title="Opportunity detail", icon="🔎")

pg = st.navigation([home, opportunities, detail])
pg.run()
