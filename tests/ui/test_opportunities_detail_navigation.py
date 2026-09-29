"""Per-row Opportunity detail links on the Opportunities queue."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from jobhunter.application.review.dtos import AssessmentDisplayState, OpportunityQueueItem
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.ui.streamlit.navigation import opportunity_detail_href
from jobhunter.ui.streamlit.opportunities_bulk import (
    OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY,
    clear_opportunity_queue_selection,
    opportunity_queue_editor_key,
)
from jobhunter.ui.streamlit.opportunities_table import build_opportunity_queue_dataframe

pytestmark = pytest.mark.integration


def _queue_item(opp_id: str, title: str) -> OpportunityQueueItem:
    return OpportunityQueueItem(
        opportunity_id=opp_id,
        title=title,
        organisation="Org",
        location=None,
        deadline=None,
        lifecycle_status=LifecycleStatus.STILL_OPEN,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        source_id="fao-external-jobs",
        source_name="FAO",
        external_url=None,
        dynamic_rank=1,
        ranking_status=RankingStatus.RANKED,
        priority_band=PriorityBand.HIGH,
        overall_relevance="high",
        source_data_sufficiency=None,
        assessment_state=AssessmentDisplayState.PRODUCTION,
        unranked_reason=None,
        exclusion_reason=None,
        last_seen_at=datetime.now(timezone.utc),
        last_processed_at=datetime.now(timezone.utc),
        review_disposition=None,
    )


def test_every_row_has_view_link_targeting_opportunity_id() -> None:
    items = [_queue_item("opp-a", "Role A"), _queue_item("opp-b", "Role B")]
    ids, df = build_opportunity_queue_dataframe(items)
    assert list(df.columns) == [
        "Select",
        "Opportunity",
        "Organisation",
        "Deadline",
        "Eligibility",
        "Rank",
        "Review",
        "View",
    ]
    assert ids == ["opp-a", "opp-b"]
    assert df["View"].tolist() == [
        opportunity_detail_href("opp-a"),
        opportunity_detail_href("opp-b"),
    ]
    assert all(row is False for row in df["Select"].tolist())


def test_detail_href_does_not_require_select_checkbox() -> None:
    href = opportunity_detail_href("opp-xyz")
    assert href == "opportunity_detail?opportunity_id=opp-xyz"
    assert "Select" not in href


def test_building_table_rows_does_not_mutate_bulk_selection_state() -> None:
    state: dict = {OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY: 0}
    key = opportunity_queue_editor_key(state)
    state[key] = {"Select": [True, False]}

    build_opportunity_queue_dataframe(
        [_queue_item("opp-1", "One"), _queue_item("opp-2", "Two")]
    )

    assert state[OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY] == 0
    assert state[key]["Select"] == [True, False]


def test_multiple_selected_rows_keep_independent_view_links() -> None:
    items = [_queue_item("sel-1", "One"), _queue_item("open-2", "Two")]
    _, df = build_opportunity_queue_dataframe(items)
    assert df.loc[1, "View"] == opportunity_detail_href("open-2")


def test_navigate_helper_does_not_clear_bulk_editor_state() -> None:
    state: dict = {OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY: 0}
    key = opportunity_queue_editor_key(state)
    state[key] = {"Select": [True]}

    with patch("jobhunter.ui.streamlit.navigation.st") as mock_st:
        from jobhunter.ui.streamlit.navigation import navigate_to_opportunity_detail

        navigate_to_opportunity_detail("opp-nav")
        mock_st.switch_page.assert_called_once()

    assert state[OPPORTUNITY_QUEUE_EDITOR_GENERATION_KEY] == 0
    assert state[key]["Select"] == [True]


def test_filtered_item_list_order_preserved_in_view_links() -> None:
    """Drill-down filters apply before row build; ids stay aligned with queue order."""
    items = [
        _queue_item("lifecycle-filtered", "Filtered role"),
    ]
    ids, df = build_opportunity_queue_dataframe(items)
    assert ids[0] == "lifecycle-filtered"
    assert "lifecycle-filtered" in df.iloc[0]["View"]
