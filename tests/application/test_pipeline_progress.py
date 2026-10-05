"""Scheduled pipeline progress logging."""

from __future__ import annotations

import io

from jobhunter.application.automation.pipeline_progress import (
    pipeline_starting,
    source_completed,
    source_failed,
)


def test_progress_messages_no_secrets_shape() -> None:
    buffer = io.StringIO()
    pipeline_starting(apply=True, trigger="SCHEDULED", stream=buffer)
    source_completed(
        "FAO",
        duration_seconds=1.25,
        retrieved=3,
        processed=2,
        stream=buffer,
    )
    source_failed(
        "developmentaid",
        duration_seconds=60.0,
        error="timed out",
        kind="TIMEOUT",
        stream=buffer,
    )
    text = buffer.getvalue()
    assert "Scheduled pipeline starting" in text
    assert "Source FAO: completed" in text
    assert "Source developmentaid: TIMEOUT" in text
