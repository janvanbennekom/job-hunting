"""Worker automation advisory lock."""

from unittest.mock import MagicMock

from jobhunter.application.automation.worker_lock import (
    JOBHUNTER_AUTOMATION_ADVISORY_LOCK_KEY,
    WorkerAutomationLock,
)


def test_try_acquire_and_release() -> None:
    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(scalar=lambda: True),
        MagicMock(),
    ]
    lock = WorkerAutomationLock(session)
    assert lock.try_acquire() is True
    lock.release()
    assert session.execute.call_count == 2
    second_call = session.execute.call_args_list[1]
    assert second_call[0][1]["key"] == JOBHUNTER_AUTOMATION_ADVISORY_LOCK_KEY


def test_context_manager_releases_on_exit() -> None:
    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(scalar=lambda: True),
        MagicMock(),
    ]
    with WorkerAutomationLock(session) as lock:
        lock.try_acquire()
    assert session.execute.call_count == 2


def test_release_when_not_held_is_noop() -> None:
    session = MagicMock()
    lock = WorkerAutomationLock(session)
    lock.release()
    session.execute.assert_not_called()
