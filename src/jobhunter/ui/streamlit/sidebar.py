"""Shared Streamlit sidebar controls."""

from __future__ import annotations

import streamlit as st

from jobhunter.infrastructure.config import Settings, get_settings
from jobhunter.ui.streamlit.bootstrap import allow_fake_results, set_allow_fake_results


def development_assessment_controls_enabled(
    settings: Settings | None = None,
) -> bool:
    """Hide fake-assessment UI in production deployments."""
    resolved = settings or get_settings()
    return not resolved.is_production()


def render_sidebar() -> None:
    with st.sidebar:
        if development_assessment_controls_enabled():
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
