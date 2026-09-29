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


def _get_bool(env_map: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = _get_var(env_map, name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    env: str
    log_level: str
    database_url: str | None
    openai_api_key: str | None
    openai_model: str | None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    smtp_use_ssl: bool = False
    smtp_starttls: bool = True
    web_base_url: str | None = None
    reliefweb_appname: str | None = None

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env_map = environ if environ is not None else os.environ
        smtp_port_raw = _get_var(env_map, "JOBHUNTER_SMTP_PORT")
        smtp_port = int(smtp_port_raw) if smtp_port_raw else None
        return cls(
            env=_get_var(env_map, "JOBHUNTER_ENV", "development") or "development",
            log_level=(
                _get_var(env_map, "JOBHUNTER_LOG_LEVEL", "INFO") or "INFO"
            ).upper(),
            database_url=resolve_database_url(env_map),
            openai_api_key=_get_var(env_map, "JOBHUNTER_OPENAI_API_KEY") or None,
            openai_model=_get_var(env_map, "JOBHUNTER_OPENAI_MODEL") or None,
            smtp_host=_get_var(env_map, "JOBHUNTER_SMTP_HOST") or None,
            smtp_port=smtp_port,
            smtp_username=_get_var(env_map, "JOBHUNTER_SMTP_USER") or None,
            smtp_password=_get_var(env_map, "JOBHUNTER_SMTP_PASSWORD") or None,
            smtp_from=_get_var(env_map, "JOBHUNTER_SMTP_FROM") or None,
            smtp_to=_get_var(env_map, "JOBHUNTER_SMTP_TO") or None,
            smtp_use_ssl=_get_bool(env_map, "JOBHUNTER_SMTP_USE_SSL"),
            smtp_starttls=_get_bool(env_map, "JOBHUNTER_SMTP_STARTTLS", True),
            web_base_url=_get_var(env_map, "JOBHUNTER_WEB_BASE_URL") or None,
            reliefweb_appname=_get_var(env_map, "JOBHUNTER_RELIEFWEB_APPNAME") or None,
        )

    def is_production(self) -> bool:
        return self.env.strip().lower() == "production"

    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from and self.smtp_to)

    def smtp_production_ready(self) -> bool:
        """SMTP sufficient for production notification delivery."""
        if not self.smtp_host or not self.smtp_from or not self.smtp_to:
            return False
        if self.smtp_port is None:
            return False
        if self.smtp_username and not self.smtp_password:
            return False
        return True

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
