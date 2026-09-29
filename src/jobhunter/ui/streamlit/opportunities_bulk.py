"""Bulk triage helpers for the Opportunities data editor (Streamlit widget state)."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

BULK_REVIEW_FLASH_KEY = "bulk_review_flash"
OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY = "opportunity_queue_editor_generation"
OPPORTUNITY_QUEUE_EDITOR_KEY_PREFIX = "opportunity_queue_editor"


def opportunity_queue_editor_key(session_state: Mapping[str, Any]) -> str:
    generation = int(session_state.get(OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY, 0))
    return f"{OPPORTUNITY_QUEUE_EDITOR_KEY_PREFIX}_{generation}"


def clear_opportunity_queue_selection(session_state: MutableMapping[str, Any]) -> None:
    """Reset ``st.data_editor`` checkbox state after a successful bulk action."""
    generation = int(session_state.get(OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY, 0))
    session_state.pop(f"{OPPORTUNITY_QUEUE_EDITOR_KEY_PREFIX}_{generation}", None)
    session_state.pop(OPPORTUNITY_QUEUE_EDITOR_KEY_PREFIX, None)
    session_state[OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY] = generation + 1


def set_bulk_review_success_flash(
    session_state: MutableMapping[str, Any], message: str
) -> None:
    session_state[BULK_REVIEW_FLASH_KEY] = message


def pop_bulk_review_flash(session_state: MutableMapping[str, Any]) -> str | None:
    value = session_state.get(BULK_REVIEW_FLASH_KEY)
    if value is None:
        return None
    session_state.pop(BULK_REVIEW_FLASH_KEY, None)
    return str(value)
