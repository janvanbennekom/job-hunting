"""DevelopmentAid scan error formatting for audit/UI."""

from __future__ import annotations

import re

_RATE_LIMIT_DETAIL = re.compile(
    r"job (\d+) detail:.*\(429\)",
    re.IGNORECASE,
)


def is_rate_limited_detail_error(message: str) -> bool:
    return "429" in message and "detail" in message.lower()


def aggregate_scan_errors(
    detail_errors: list[str],
    processing_errors: list[str],
) -> tuple[str | None, list[str]]:
    """
    Build a short operator-facing summary and optional diagnostic lines.

    Full per-job lines are returned in diagnostics for expanders/logs.
    """
    diagnostics = list(detail_errors) + list(processing_errors)
    if not diagnostics:
        return None, []

    rate_limited = [e for e in detail_errors if is_rate_limited_detail_error(e)]
    other_detail = [e for e in detail_errors if e not in rate_limited]
    parts: list[str] = []

    if rate_limited:
        job_ids = []
        for err in rate_limited:
            match = _RATE_LIMIT_DETAIL.search(err)
            if match:
                job_ids.append(match.group(1))
        count = len(rate_limited)
        summary = (
            f"{count} detail request(s) were rate-limited (HTTP 429). "
            "List-level opportunity data was retained."
        )
        if job_ids:
            shown = ", ".join(job_ids[:8])
            if len(job_ids) > 8:
                shown += f", … (+{len(job_ids) - 8} more)"
            summary += f" Affected job id(s): {shown}."
        parts.append(summary)

    if other_detail:
        parts.append(
            f"{len(other_detail)} detail request(s) failed (non-rate-limit)."
        )

    if processing_errors:
        parts.append(
            f"{len(processing_errors)} opportunity processing error(s)."
        )

    return " ".join(parts), diagnostics


_DIAGNOSTICS_MARKER = "\n<!--developmentaid-diagnostics-->\n"


def format_error_summary_for_storage(
    summary: str | None, diagnostics: list[str]
) -> str | None:
    if not summary:
        return None
    if not diagnostics:
        return summary[:4000]
    combined = summary + _DIAGNOSTICS_MARKER + "\n".join(diagnostics)
    return combined[:4000]


def split_stored_error_summary(text: str) -> tuple[str, list[str]]:
    if _DIAGNOSTICS_MARKER not in text:
        return text, []
    head, tail = text.split(_DIAGNOSTICS_MARKER, 1)
    lines = [line for line in tail.splitlines() if line.strip()]
    return head.strip(), lines
