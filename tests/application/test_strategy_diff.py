"""Unit tests for strategy diff."""

from __future__ import annotations

from jobhunter.application.strategy_conversation.diff import build_strategy_diff
from jobhunter.domain import PreferenceStrength, SearchTheme
from jobhunter.domain.revision_content_bundle import RevisionContentBundle


def test_diff_detects_theme_strength_change() -> None:
    revision_id = "rev-1"
    before = RevisionContentBundle(
        themes=(
            SearchTheme(
                id="t1",
                revision_id=revision_id,
                theme_key="lis",
                label="LIS",
                strength=PreferenceStrength.PREFERRED,
            ),
        ),
        criteria=(),
        exclusions=(),
    )
    after = RevisionContentBundle(
        themes=(
            SearchTheme(
                id="t2",
                revision_id=revision_id,
                theme_key="lis",
                label="LIS",
                strength=PreferenceStrength.STRONGLY_PREFERRED,
            ),
        ),
        criteria=(),
        exclusions=(),
    )
    lines = build_strategy_diff(before, after)
    assert len(lines) == 1
    assert lines[0].field_name == "strength"
