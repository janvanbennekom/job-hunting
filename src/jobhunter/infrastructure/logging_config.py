"""Basic logging configuration for JobHunter."""

from __future__ import annotations

import logging
import sys

from jobhunter.infrastructure.config import Settings, get_settings

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(
    settings: Settings | None = None,
    *,
    level: str | None = None,
) -> None:
    """Configure root logging once for CLI and worker entry points."""
    resolved = settings or get_settings()
    log_level = (level or resolved.log_level).upper()
    numeric = getattr(logging, log_level, logging.INFO)

    root = logging.getLogger()
    if root.handlers:
        root.setLevel(numeric)
        return

    logging.basicConfig(
        level=numeric,
        format=_DEFAULT_FORMAT,
        stream=sys.stderr,
    )
