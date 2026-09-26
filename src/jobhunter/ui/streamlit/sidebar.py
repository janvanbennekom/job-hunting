"""Shared Streamlit sidebar controls."""

from __future__ import annotations

import streamlit as st

from jobhunter.ui.streamlit.bootstrap import allow_fake_results, set_allow_fake_results


def render_sidebar() -> None:
    with st.sidebar:
        st.header("View options")
        fake = st.checkbox(
            "Show development/fake assessments & rankings",
            value=allow_fake_results(),
        )
        set_allow_fake_results(fake)
        if fake:
            st.error(
                "Development mode: fake assessments and fake-derived rankings "
                "are visible. Not production results."
            )
