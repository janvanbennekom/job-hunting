"""Shared HTTP timeout defaults and bounded urllib access."""

from __future__ import annotations

import os
import urllib.request

DEFAULT_CONNECT_TIMEOUT_SECONDS = float(
    os.environ.get("JOBHUNTER_HTTP_CONNECT_TIMEOUT", "15")
)
DEFAULT_READ_TIMEOUT_SECONDS = float(
    os.environ.get("JOBHUNTER_HTTP_READ_TIMEOUT", "90")
)


def http_timeout(
    read_seconds: float,
    *,
    connect_seconds: float | None = None,
) -> tuple[float, float]:
    """Return (connect_timeout, read_timeout) for connector clients."""
    connect = (
        connect_seconds
        if connect_seconds is not None
        else DEFAULT_CONNECT_TIMEOUT_SECONDS
    )
    return (connect, read_seconds)


def timeout_settings_report() -> dict[str, float]:
    """Read-only summary for diagnostics (no network)."""
    return {
        "connect_seconds_default": DEFAULT_CONNECT_TIMEOUT_SECONDS,
        "read_seconds_default": DEFAULT_READ_TIMEOUT_SECONDS,
    }


def _open_with_timeouts(
    opener: urllib.request.OpenerDirector | None,
    request: urllib.request.Request,
    *,
    connect_timeout: float,
    read_timeout: float,
):
    timeout: float | tuple[float, float] = (connect_timeout, read_timeout)
    try:
        if opener is None:
            return urllib.request.urlopen(request, timeout=timeout)
        return opener.open(request, timeout=timeout)
    except TypeError:
        if opener is None:
            return urllib.request.urlopen(request, timeout=read_timeout)
        return opener.open(request, timeout=read_timeout)


def urlopen_with_timeouts(
    request: urllib.request.Request,
    *,
    read_seconds: float,
    connect_seconds: float | None = None,
):
    connect, read = http_timeout(read_seconds, connect_seconds=connect_seconds)
    return _open_with_timeouts(
        None,
        request,
        connect_timeout=connect,
        read_timeout=read,
    )


def opener_open_with_timeouts(
    opener: urllib.request.OpenerDirector,
    request: urllib.request.Request,
    *,
    read_seconds: float,
    connect_seconds: float | None = None,
):
    connect, read = http_timeout(read_seconds, connect_seconds=connect_seconds)
    return _open_with_timeouts(
        opener,
        request,
        connect_timeout=connect,
        read_timeout=read,
    )
