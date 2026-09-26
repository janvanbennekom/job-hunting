"""Streamlit session and database bootstrap."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker

from jobhunter.infrastructure.config import get_settings
from jobhunter.infrastructure.persistence.database import (
    create_engine_from_settings,
    create_session_factory,
)


def _load_dotenv_if_present() -> None:
    root = Path(__file__).resolve().parents[4]
    env_path = root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@st.cache_resource
def get_session_factory() -> sessionmaker[Session]:
    _load_dotenv_if_present()
    settings = get_settings()
    settings.require_database_url()
    engine = create_engine_from_settings(settings)
    return create_session_factory(engine)


def allow_fake_results() -> bool:
    return bool(st.session_state.get("allow_fake_results", False))


def set_allow_fake_results(value: bool) -> None:
    st.session_state["allow_fake_results"] = value
