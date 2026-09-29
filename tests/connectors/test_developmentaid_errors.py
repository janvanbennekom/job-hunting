from jobhunter.connectors.developmentaid.errors import (
    aggregate_scan_errors,
    format_error_summary_for_storage,
    split_stored_error_summary,
)


def test_aggregate_rate_limit_detail_errors() -> None:
    detail = [
        "job 1808721 detail: HTTP 429 Too Many Attempts (4 attempt(s))",
        "job 1808720 detail: HTTP 429 Too Many Attempts (4 attempt(s))",
    ]
    summary, diagnostics = aggregate_scan_errors(detail, [])
    assert summary is not None
    assert "2 detail request(s) were rate-limited" in summary
    assert "List-level opportunity data was retained" in summary
    assert len(diagnostics) == 2


def test_storage_round_trip() -> None:
    summary, diagnostics = aggregate_scan_errors(
        ["job 1 detail: HTTP 429"], []
    )
    stored = format_error_summary_for_storage(summary, diagnostics)
    assert stored
    head, lines = split_stored_error_summary(stored)
    assert "rate-limited" in head
    assert lines
