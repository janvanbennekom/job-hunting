"""Environment-based configuration (stdlib only)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


def _get_var(
    env_map: Mapping[str, str],
    name: str,
    default: str | None = None,
) -> str | None:
    value = env_map.get(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    env: str
    log_level: str
    database_url: str | None
    openai_api_key: str | None

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env_map = environ if environ is not None else os.environ
        return cls(
            env=_get_var(env_map, "JOBHUNTER_ENV", "development") or "development",
            log_level=(
                _get_var(env_map, "JOBHUNTER_LOG_LEVEL", "INFO") or "INFO"
            ).upper(),
            database_url=_get_var(env_map, "JOBHUNTER_DATABASE_URL") or None,
            openai_api_key=_get_var(env_map, "JOBHUNTER_OPENAI_API_KEY") or None,
        )


def get_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Return settings for the current process environment."""
    return Settings.from_environ(environ)
