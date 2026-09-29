"""DevelopmentAid HTTP rate-limit and retry policy (detail/search JSON API)."""

from __future__ import annotations

import email.utils
import time
from dataclasses import dataclass
from typing import Mapping

# Observed on public detail API (2026-09-29): X-RateLimit-Limit: 20
DEFAULT_DETAIL_INTERVAL_SECONDS = 3.0
DEFAULT_MAX_RATE_LIMIT_RETRIES = 3
DEFAULT_BACKOFF_BASE_SECONDS = 2.0
DEFAULT_BACKOFF_MAX_SECONDS = 60.0
DEFAULT_MAX_RETRY_AFTER_SECONDS = 120.0
DEFAULT_CONSECUTIVE_RATE_LIMIT_STOP = 2


@dataclass(frozen=True, slots=True)
class DevelopmentAidHttpPolicy:
    """Connector-level policy; not stored in automation.json."""

    detail_interval_seconds: float = DEFAULT_DETAIL_INTERVAL_SECONDS
    max_rate_limit_retries: int = DEFAULT_MAX_RATE_LIMIT_RETRIES
    backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS
    backoff_max_seconds: float = DEFAULT_BACKOFF_MAX_SECONDS
    max_retry_after_seconds: float = DEFAULT_MAX_RETRY_AFTER_SECONDS
    consecutive_rate_limit_stop: int = DEFAULT_CONSECUTIVE_RATE_LIMIT_STOP


def parse_retry_after(
    header_value: str | None, *, now: float | None = None
) -> float | None:
    """Return seconds to wait from Retry-After (delta or HTTP-date)."""
    if not header_value or not str(header_value).strip():
        return None
    text = str(header_value).strip()
    try:
        seconds = float(text)
        return max(0.0, seconds)
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(text)
        reference = now if now is not None else time.time()
        wait = parsed.timestamp() - reference
        return max(0.0, wait)
    except (TypeError, ValueError, OverflowError):
        return None


def backoff_seconds(
    attempt_index: int,
    *,
    base: float = DEFAULT_BACKOFF_BASE_SECONDS,
    maximum: float = DEFAULT_BACKOFF_MAX_SECONDS,
) -> float:
    """Exponential backoff for attempt_index 0, 1, 2, … (no jitter)."""
    if attempt_index < 0:
        return base
    return min(maximum, base * (2**attempt_index))


def rate_limit_wait_seconds(
    attempt_index: int,
    headers: Mapping[str, str],
    policy: DevelopmentAidHttpPolicy,
) -> float:
    retry_after = parse_retry_after(headers.get("Retry-After"))
    if retry_after is not None:
        return min(retry_after, policy.max_retry_after_seconds)
    return backoff_seconds(
        attempt_index,
        base=policy.backoff_base_seconds,
        maximum=policy.backoff_max_seconds,
    )
