"""Strategy presentation DTO tests (Phase 15)."""

from __future__ import annotations

from jobhunter.application.strategy_conversation.dtos import ActiveStrategyView
from jobhunter.application.strategy_display.presentation import build_strategy_presentation


def test_build_strategy_presentation_groups_criteria() -> None:
    active = ActiveStrategyView(
        owner_key="owner",
        strategy_id="strategy-1",
        current_revision_id="rev-1",
        revision_number=1,
        change_summary="Seed",
        content_hash="hash",
        themes=[
            {
                "theme_key": "lis",
                "label": "LIS",
                "strength": "STRONGLY_PREFERRED",
                "is_active": True,
                "notes": "Primary focus",
            }
        ],
        criteria=[
            {
                "category": "PREFERENCE",
                "code": "TRAVEL_PATTERN",
                "strength": "PREFERRED",
                "is_active": True,
                "value": {"aspect": "continuous_abroad"},
            },
            {
                "category": "HARD_CONSTRAINT",
                "code": "ASSIGNMENT_DURATION",
                "strength": "PREFERRED",
                "is_active": True,
                "value": {"min_months": 3},
            },
        ],
        exclusions=[
            {
                "exclusion_code": "VOLUNTEER",
                "is_active": True,
                "parameters": None,
            }
        ],
    )
    view = build_strategy_presentation(active)
    assert len(view.theme_rows) == 1
    assert view.theme_rows[0].strength == "Strong"
    assert len(view.preference_rows) == 1
    assert len(view.constraint_rows) == 1
    assert view.exclusion_rows[0].exclusion == "Volunteer"
