"""Environment-based configuration (stdlib only)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import quote_plus


def _get_var(
    env_map: Mapping[str, str],
    name: str,
    default: str | None = None,
) -> str | None:
    value = env_map.get(name)
    if value is None or value == "":
        return default
    return value


def resolve_database_url(env_map: Mapping[str, str]) -> str | None:
    """Resolve DB URL from JOBHUNTER_DATABASE_URL or POSTGRES_* components."""
    direct = _get_var(env_map, "JOBHUNTER_DATABASE_URL")
    if direct:
        return direct

    host = _get_var(env_map, "POSTGRES_HOST")
    port = _get_var(env_map, "POSTGRES_PORT", "5432") or "5432"
    database = _get_var(env_map, "POSTGRES_DB")
    user = _get_var(env_map, "POSTGRES_USER")
    password = _get_var(env_map, "POSTGRES_PASSWORD")
    if host and database and user and password:
        user_q = quote_plus(user)
        password_q = quote_plus(password)
        return (
            f"postgresql+psycopg://{user_q}:{password_q}@{host}:{port}/{database}"
        )
    return None


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    env: str
    log_level: str
    database_url: str | None
    openai_api_key: str | None
    openai_model: str | None

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env_map = environ if environ is not None else os.environ
        return cls(
            env=_get_var(env_map, "JOBHUNTER_ENV", "development") or "development",
            log_level=(
                _get_var(env_map, "JOBHUNTER_LOG_LEVEL", "INFO") or "INFO"
            ).upper(),
            database_url=resolve_database_url(env_map),
            openai_api_key=_get_var(env_map, "JOBHUNTER_OPENAI_API_KEY") or None,
            openai_model=_get_var(env_map, "JOBHUNTER_OPENAI_MODEL") or None,
        )

    def require_database_url(self) -> str:
        if not self.database_url:
            raise RuntimeError(
                "Database URL is not configured. Set JOBHUNTER_DATABASE_URL or "
                "POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, and "
                "POSTGRES_PASSWORD."
            )
        return self.database_url


def get_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Return settings for the current process environment."""
    return Settings.from_environ(environ)
