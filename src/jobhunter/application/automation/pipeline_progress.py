"""Structured stdout progress for scheduled automation (no secrets)."""

from __future__ import annotations

import sys
from typing import TextIO


def _emit(message: str, *, stream: TextIO | None = None) -> None:
    out = stream if stream is not None else sys.stdout
    print(message, file=out, flush=True)


def pipeline_starting(
    *, apply: bool, trigger: str, stream: TextIO | None = None
) -> None:
    mode = "apply" if apply else "dry-run"
    _emit(f"Scheduled pipeline starting ({mode}, trigger={trigger})...", stream=stream)


def pipeline_completed(
    *, exit_code: int, run_id: str | None, stream: TextIO | None = None
) -> None:
    suffix = f" run_id={run_id}" if run_id else ""
    _emit(
        f"Scheduled pipeline completed exit_code={exit_code}{suffix}",
        stream=stream,
    )


def source_starting(source_key: str, *, stream: TextIO | None = None) -> None:
    _emit(f"Source {source_key}: starting", stream=stream)


def source_completed(
    source_key: str,
    *,
    duration_seconds: float,
    retrieved: int,
    processed: int,
    stream: TextIO | None = None,
) -> None:
    _emit(
        f"Source {source_key}: completed "
        f"retrieved={retrieved} processed={processed} duration={duration_seconds:.1f}s",
        stream=stream,
    )


def source_failed(
    source_key: str,
    *,
    duration_seconds: float,
    error: str,
    kind: str = "FAILED",
    stream: TextIO | None = None,
) -> None:
    concise = _concise_error(error)
    _emit(
        f"Source {source_key}: {kind} duration={duration_seconds:.1f}s "
        f"error={concise}",
        stream=stream,
    )


def phase_starting(phase: str, *, stream: TextIO | None = None) -> None:
    _emit(f"Pipeline phase: {phase} starting", stream=stream)


def phase_completed(phase: str, *, stream: TextIO | None = None, **kwargs: int | str) -> None:
    parts = " ".join(f"{key}={value}" for key, value in kwargs.items())
    suffix = f" {parts}" if parts else ""
    _emit(f"Pipeline phase: {phase} completed{suffix}", stream=stream)


def _concise_error(message: str, max_len: int = 200) -> str:
    text = " ".join(message.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
