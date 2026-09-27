"""PostgreSQL advisory lock for single-flight scheduled automation runs."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Stable 63-bit key for JobHunter automation (single global lock).
JOBHUNTER_AUTOMATION_ADVISORY_LOCK_KEY = 4_815_162_342


class WorkerAutomationLock:
    """Try-acquire advisory lock; always release on context exit."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._held = False

    def try_acquire(self) -> bool:
        row = self._session.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": JOBHUNTER_AUTOMATION_ADVISORY_LOCK_KEY},
        ).scalar()
        self._held = bool(row)
        return self._held

    def release(self) -> None:
        if not self._held:
            return
        self._session.execute(
            text("SELECT pg_advisory_unlock(:key)"),
            {"key": JOBHUNTER_AUTOMATION_ADVISORY_LOCK_KEY},
        )
        self._held = False

    def __enter__(self) -> WorkerAutomationLock:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
