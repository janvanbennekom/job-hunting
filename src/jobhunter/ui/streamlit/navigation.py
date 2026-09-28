"""Streamlit navigation and query-parameter helpers (Phase 15)."""

from __future__ import annotations

import streamlit as st

from jobhunter.infrastructure.web_urls import parse_opportunity_id_from_query

OPPORTUNITIES_PAGE = "pages/opportunities.py"
OPPORTUNITY_DETAIL_PAGE = "pages/opportunity_detail.py"


def get_query_param(key: str) -> str | None:
    raw = st.query_params.get(key)
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw[0].strip() if raw and str(raw[0]).strip() else None
    text = str(raw).strip()
    return text or None


def navigate_to_opportunities(**filters: str) -> None:
    st.query_params.from_dict(
        {key: str(value) for key, value in filters.items() if value}
    )
    st.switch_page(OPPORTUNITIES_PAGE)


def navigate_to_opportunity_detail(opportunity_id: str) -> None:
    st.session_state["selected_opportunity_id"] = opportunity_id
    st.query_params.from_dict({"opportunity_id": opportunity_id})
    st.switch_page(OPPORTUNITY_DETAIL_PAGE)


def resolve_opportunity_id_from_url() -> str | None:
    qp = {k: get_query_param(k) or "" for k in ("opportunity_id", "id")}
    return parse_opportunity_id_from_query(qp)
