"""Read-only deployment checks for profile assessment (no OpenAI calls)."""

from __future__ import annotations

import argparse
import json
import sys

from _script_bootstrap import bootstrap_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    bootstrap_repo()

    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import text

    from jobhunter.domain.assessment_enums import PROFILE_ASSESSMENT_SCHEMA_VERSION
    from jobhunter.infrastructure.automation.config import (
        load_automation_config,
        resolve_config_path,
    )
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    settings = get_settings()
    settings.require_database_url()
    automation = load_automation_config()
    config_path = resolve_config_path()

    openai_configured = bool(settings.openai_api_key and settings.openai_model)
    report = {
        "jobhunter_env": settings.env,
        "openai_model": settings.openai_model if settings.openai_model else None,
        "openai_configured": openai_configured,
        "profile_assessment_schema_version": PROFILE_ASSESSMENT_SCHEMA_VERSION,
        "production_assessment_enabled": automation.pipeline.production_assessment_enabled,
        "assessment_required": automation.pipeline.assessment_required,
        "automation_config_path": str(config_path) if config_path else None,
    }

    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    try:
        with session_scope(session_factory) as session:
            row = session.execute(
                text("SELECT version_num FROM alembic_version")
            ).first()
            report["alembic_version"] = row[0] if row else None
    finally:
        engine.dispose()

    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(repo / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_cfg)
    report["alembic_head_revision"] = script.get_current_head()

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"JOBHUNTER_ENV: {report['jobhunter_env']}")
    print(f"OpenAI model: {report['openai_model'] or '(not set)'}")
    print(f"OpenAI configured: {report['openai_configured']}")
    print(f"Assessment schema: {report['profile_assessment_schema_version']}")
    print(
        f"production_assessment_enabled: {report['production_assessment_enabled']}"
    )
    print(f"assessment_required: {report['assessment_required']}")
    print(f"automation config: {report['automation_config_path']}")
    print(f"database alembic_version: {report['alembic_version']}")
    print(f"repository alembic head: {report['alembic_head_revision']}")
    if report["alembic_version"] != report["alembic_head_revision"]:
        print(
            "WARNING: database revision does not match repository head.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
