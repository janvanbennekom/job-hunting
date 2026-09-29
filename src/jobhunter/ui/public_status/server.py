"""Minimal public HTTP server for aggregate JobHunter status (no authentication)."""

from __future__ import annotations

import os
from http import HTTPStatus
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from jobhunter.application.review.dashboard_summary import DashboardSummaryService
from jobhunter.infrastructure.config import get_settings
from jobhunter.infrastructure.persistence.database import (
    create_engine_from_settings,
    create_session_factory,
    session_scope,
)
from jobhunter.ui.public_status.html import render_public_status_html

_STATUS_PATHS = frozenset({"/", "/status", "/status/"})
_HEALTH_PATHS = frozenset({"/health", "/health/"})

_engine = None
_session_factory = None


class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def _session_factory_singleton():
    global _engine, _session_factory
    if _session_factory is None:
        settings = get_settings()
        settings.require_database_url()
        _engine = create_engine_from_settings(settings)
        _session_factory = create_session_factory(_engine)
    return _session_factory


def _build_status_html() -> str:
    session_factory = _session_factory_singleton()
    with session_scope(session_factory) as session:
        summary = DashboardSummaryService(session).build_summary(
            allow_fake=False,
            include_queue_preview=False,
            include_latest_scan=False,
        )
    return render_public_status_html(summary)


def application(environ, start_response):  # noqa: ANN001
    path = environ.get("PATH_INFO") or "/"
    if path in _HEALTH_PATHS:
        body = b"OK"
        start_response(
            f"{HTTPStatus.OK.value} OK",
            [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]

    if path not in _STATUS_PATHS:
        body = b"Not Found"
        start_response(
            f"{HTTPStatus.NOT_FOUND.value} Not Found",
            [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]

    try:
        html = _build_status_html()
        body = html.encode("utf-8")
        start_response(
            f"{HTTPStatus.OK.value} OK",
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [body]
    except Exception:  # noqa: BLE001
        body = b"Service Unavailable"
        start_response(
            f"{HTTPStatus.SERVICE_UNAVAILABLE.value} Service Unavailable",
            [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]


def main() -> None:
    host = os.environ.get("JOBHUNTER_STATUS_BIND", "0.0.0.0")
    port = int(os.environ.get("JOBHUNTER_STATUS_PORT", "8502"))
    with make_server(host, port, application, server_class=_ThreadingWSGIServer) as httpd:
        print(f"JobHunter public status on http://{host}:{port}/status", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
