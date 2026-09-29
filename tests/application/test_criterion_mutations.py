"""Structured strategy criterion mutation builder."""

from jobhunter.application.strategy_structured_edit.criterion_mutations import (
    build_criterion_mutations,
)


def test_build_criterion_mutations_detects_value_change() -> None:
    originals = [
        {
            "category": "PREFERENCE",
            "code": "WORK_MODE",
            "value": {
                "remote": "PREFERRED",
                "hybrid": "ACCEPTABLE",
                "on_site": "LESS_PREFERRED",
            },
            "strength": None,
        }
    ]
    edited = [
        {
            "category": "PREFERENCE",
            "code": "WORK_MODE",
            "value": {
                "remote": "STRONGLY_PREFERRED",
                "hybrid": "ACCEPTABLE",
                "on_site": "LESS_PREFERRED",
            },
            "strength": None,
        }
    ]
    mutations = build_criterion_mutations(originals, edited)
    assert len(mutations) == 1
    assert mutations[0]["op"] == "SET_CRITERION"
    assert mutations[0]["value"]["remote"] == "STRONGLY_PREFERRED"


def test_build_criterion_mutations_no_op() -> None:
    item = {
        "category": "PREFERENCE",
        "code": "TRAVEL_PATTERN",
        "value": {"aspect": "continuous_abroad"},
        "strength": None,
    }
    assert build_criterion_mutations([item], [item]) == []
