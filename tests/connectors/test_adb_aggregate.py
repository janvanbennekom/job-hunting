from jobhunter.connectors.adb.aggregate import aggregate_notice_records


def _row(
    notice_id: str,
    expertise: str,
    *,
    row_index: int,
) -> dict:
    return {
        "notice_id": notice_id,
        "title": f"TA-1 CAM: Example ({notice_id})",
        "expertise": expertise,
        "consultant_type": "Firm",
        "row_index": row_index,
    }


def test_merge_expertise_for_shared_notice_id() -> None:
    rows = [
        _row("E-059508-001", "Land Administration Specialist", row_index=2),
        _row("E-059508-001", "GIS Specialist", row_index=0),
        _row("E-059508-001", "Survey Specialist", row_index=1),
    ]
    merged = aggregate_notice_records(rows)
    assert len(merged) == 1
    assert merged[0]["notice_id"] == "E-059508-001"
    assert merged[0]["expertise_lines"] == [
        "GIS Specialist",
        "Land Administration Specialist",
        "Survey Specialist",
    ]


def test_aggregate_order_independent() -> None:
    rows_a = [
        _row("E-059508-001", "B skill", row_index=1),
        _row("E-059508-001", "A skill", row_index=0),
    ]
    rows_b = list(reversed(rows_a))
    assert aggregate_notice_records(rows_a) == aggregate_notice_records(rows_b)


def test_deduplicate_expertise_case_insensitive() -> None:
    rows = [
        _row("E-000001-001", "GIS", row_index=0),
        _row("E-000001-001", "gis", row_index=1),
    ]
    merged = aggregate_notice_records(rows)
    assert merged[0]["expertise_lines"] == ["GIS"]


def test_single_row_unchanged_expertise() -> None:
    row = _row("E-000002-001", "Only one", row_index=0)
    merged = aggregate_notice_records([row])
    assert merged[0]["expertise"] == "Only one"
    assert merged[0]["expertise_lines"] == ["Only one"]


def test_reaggregate_preserves_expertise_lines() -> None:
    first_pass = aggregate_notice_records(
        [
            _row("E-059508-001", "A", row_index=0),
            _row("E-059508-001", "B", row_index=1),
        ]
    )
    second_pass = aggregate_notice_records(first_pass)
    assert second_pass[0]["expertise_lines"] == ["A", "B"]


def test_distinct_notice_ids_remain_separate() -> None:
    rows = [
        _row("E-000001-001", "A", row_index=0),
        _row("E-000002-001", "B", row_index=0),
    ]
    merged = aggregate_notice_records(rows)
    assert len(merged) == 2
