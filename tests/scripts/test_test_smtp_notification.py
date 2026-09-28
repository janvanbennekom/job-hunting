"""SMTP test script behaviour."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from jobhunter.infrastructure.config import Settings

_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    sys.path.insert(0, str(_ROOT / "src"))
    path = _ROOT / "scripts" / "test_smtp_notification.py"
    spec = importlib.util.spec_from_file_location("test_smtp_notification", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dry_run_does_not_send() -> None:
    mod = _load_script_module()
    settings = Settings(
        env="development",
        log_level="INFO",
        database_url=None,
        openai_api_key=None,
        openai_model=None,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_from="from@example.com",
        smtp_to="to@example.com",
    )
    mock_sender = MagicMock()
    with (
        patch(
            "jobhunter.infrastructure.config.get_settings",
            return_value=settings,
        ),
        patch(
            "jobhunter.application.automation.notification_factory.resolve_notification_sender",
            return_value=mock_sender,
        ),
    ):
        code = mod.main(["--dry-run"])
    assert code == 0
    mock_sender.send.assert_not_called()
