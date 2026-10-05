"""Read-only report of automation source order and HTTP timeout settings."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    import os

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report enabled automation sources and connector HTTP timeouts (no network)."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Automation JSON (default: JOBHUNTER_AUTOMATION_CONFIG or built-in)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    from jobhunter.connectors.developmentaid.http_policy import DevelopmentAidHttpPolicy
    from jobhunter.connectors.http_timeout import http_timeout, timeout_settings_report
    from jobhunter.infrastructure.automation.config import load_automation_config

    config = load_automation_config(path=args.config)
    defaults = timeout_settings_report()

    print("HTTP timeout defaults (env JOBHUNTER_HTTP_* may override connect):")
    print(f"  connect_seconds={defaults['connect_seconds_default']}")
    print(f"  read_seconds_default={defaults['read_seconds_default']}")
    print()

    # Per-connector read timeouts (constructor defaults; no HTTP).
    client_read_seconds: dict[str, float] = {
        "fao": 60.0,
        "developmentaid": 60.0,
        "worldbank": 60.0,
        "undp": 60.0,
        "afdb": 60.0,
        "adb": 90.0,
        "reliefweb": 60.0,
        "ted": 90.0,
    }

    print("Enabled source execution order:")
    for index, source in enumerate(config.enabled_sources(), start=1):
        read_seconds = client_read_seconds.get(source.key, 60.0)
        connect, read = http_timeout(read_seconds)
        extra = ""
        if source.key == "developmentaid":
            policy = DevelopmentAidHttpPolicy()
            extra = (
                f" detail_interval={policy.detail_interval_seconds}s"
                f" max_rate_limit_retries={policy.max_rate_limit_retries}"
            )
        print(
            f"  {index}. {source.key} limit={source.limit}"
            f" fetch_details={source.fetch_details}"
            f" http_connect={connect}s http_read={read}s{extra}"
        )

    print()
    print(
        "Pipeline flags: "
        f"production_assessment_enabled={config.pipeline.production_assessment_enabled} "
        f"ranking_enabled={config.pipeline.ranking_enabled}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
