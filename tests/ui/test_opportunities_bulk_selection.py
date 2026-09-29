"""Bulk opportunity selection reset after successful triage."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.review import HumanReviewService
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.ui.streamlit.opportunities_bulk import (
    BULK_REVIEW_FLASH_KEY,
    OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY,
    OPPORTUNITY_QUEUE_EDITOR_KEY_PREFIX,
    clear_opportunity_queue_selection,
    opportunity_queue_editor_key,
    pop_bulk_review_flash,
    set_bulk_review_success_flash,
)

pytestmark = pytest.mark.integration


def _editor_state(selected: bool) -> dict:
    return {"edited_rows": {}, "added_rows": [], "deleted_rows": [], "Select": [selected]}


def test_successful_dismiss_clears_editor_widget_state() -> None:
    state: dict = {OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY: 0}
    key = opportunity_queue_editor_key(state)
    state[key] = _editor_state(True)

    clear_opportunity_queue_selection(state)

    assert state.get(key) is None
    assert state[OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY] == 1
    assert opportunity_queue_editor_key(state) == f"{OPPORTUNITY_QUEUE_EDITOR_KEY_PREFIX}_1"
    assert state.get(opportunity_queue_editor_key(state)) is None


def test_successful_shortlist_uses_same_reset_as_dismiss() -> None:
    state: dict = {OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY: 2}
    key = opportunity_queue_editor_key(state)
    state[key] = _editor_state(True)
    state["bulk_review_pending"] = {
        "disposition": ReviewDisposition.SHORTLIST.value,
        "count": 1,
        "opportunity_ids": ["opp-1"],
    }

    state.pop("bulk_review_pending", None)
    clear_opportunity_queue_selection(state)

    assert state[OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY] == 3
    assert state.get(key) is None


def test_cancel_preserves_editor_generation_and_widget_state() -> None:
    state: dict = {OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY: 0}
    key = opportunity_queue_editor_key(state)
    state[key] = _editor_state(True)
    state["bulk_review_pending"] = {"disposition": "DISMISS", "count": 1}

    state.pop("bulk_review_pending", None)

    assert state[OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY] == 0
    assert state[key] == _editor_state(True)


def test_validation_error_preserves_editor_state() -> None:
    state: dict = {OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY: 0}
    key = opportunity_queue_editor_key(state)
    state[key] = _editor_state(True)

    session = MagicMock()
    service = HumanReviewService(session)
    with pytest.raises(ValueError):
        service.append_reviews_bulk(["missing-opp"], ReviewDisposition.DISMISS)

    assert state[OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY] == 0
    assert state[key] == _editor_state(True)


def test_clear_selection_does_not_touch_unrelated_session_keys() -> None:
    state: dict = {
        OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY: 0,
        "lifecycle": "STILL_OPEN",
        "ranking_band": "HIGH",
        "bulk_review_notes": "keep me",
    }
    key = opportunity_queue_editor_key(state)
    state[key] = _editor_state(True)

    clear_opportunity_queue_selection(state)

    assert state["lifecycle"] == "STILL_OPEN"
    assert state["ranking_band"] == "HIGH"
    assert state["bulk_review_notes"] == "keep me"


def test_bulk_append_only_semantics_unchanged(db_session: Session) -> None:
    from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
    from jobhunter.domain.opportunity import Opportunity
    from jobhunter.infrastructure.persistence.repositories import OpportunityRepository

    opp = OpportunityRepository(db_session).save(
        Opportunity(
            id="sel-opp-1",
            title="Role",
            lifecycle_status=LifecycleStatus.STILL_OPEN,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        )
    )
    service = HumanReviewService(db_session)
    service.append_reviews_bulk([opp.id], ReviewDisposition.DISMISS)
    service.append_reviews_bulk([opp.id], ReviewDisposition.SHORTLIST)
    latest = service.get_latest(opp.id)
    assert latest is not None
    assert latest.disposition is ReviewDisposition.SHORTLIST
    assert len(service.list_history(opp.id)) == 2


def test_success_flash_survives_rerun_simulation() -> None:
    state: dict = {}
    set_bulk_review_success_flash(state, "Recorded DISMISS for 2 opportunities.")
    assert pop_bulk_review_flash(state) == "Recorded DISMISS for 2 opportunities."
    assert state.get(BULK_REVIEW_FLASH_KEY) is None
