from jobhunter.connectors.developmentaid.http_policy import (
    backoff_seconds,
    parse_retry_after,
    rate_limit_wait_seconds,
)
from jobhunter.connectors.developmentaid.http_policy import DevelopmentAidHttpPolicy


def test_parse_retry_after_delta_seconds() -> None:
    assert parse_retry_after("4") == 4.0


def test_backoff_exponential() -> None:
    assert backoff_seconds(0) == 2.0
    assert backoff_seconds(1) == 4.0
    assert backoff_seconds(2) == 8.0


def test_rate_limit_wait_prefers_retry_after() -> None:
    policy = DevelopmentAidHttpPolicy()
    wait = rate_limit_wait_seconds(0, {"Retry-After": "5"}, policy)
    assert wait == 5.0
