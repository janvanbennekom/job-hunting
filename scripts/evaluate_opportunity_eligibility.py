"""Evaluate opportunity eligibility against the active search strategy."""

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity-id", help="Evaluate one opportunity by id")
    parser.add_argument(
        "--source-id",
        default="fao-external-jobs",
        help="Evaluate all opportunities linked to this JobSource",
    )
    parser.add_argument(
        "--all-linked",
        action="store_true",
        help="Evaluate every opportunity with a source link (use with care)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    from sqlalchemy import select

    from jobhunter.application.eligibility import EligibilityFilterService
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    from jobhunter.infrastructure.persistence.eligibility_repositories import (
        EligibilityRuleResultRepository,
    )
    from jobhunter.infrastructure.persistence.models import OpportunitySourceRow

    get_settings().require_database_url()
    engine = create_engine_from_settings()
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            service = EligibilityFilterService(session)
            opportunity_ids: list[str] = []
            if args.opportunity_id:
                opportunity_ids = [args.opportunity_id]
            else:
                stmt = select(OpportunitySourceRow.opportunity_id).distinct()
                if not args.all_linked:
                    stmt = stmt.where(
                        OpportunitySourceRow.source_id == args.source_id
                    )
                opportunity_ids = list(session.scalars(stmt).all())

            if not opportunity_ids:
                print("No opportunities matched.")
                return 0

            for opp_id in opportunity_ids:
                result = service.evaluate_and_persist(opp_id)
                print(
                    f"{opp_id}: {result.decision.status.value} "
                    f"(decision {result.decision.id}, "
                    f"revision {result.decision.search_strategy_revision_id})"
                )
                rules = EligibilityRuleResultRepository(session).list_for_decision(
                    result.decision.id
                )
                for rule in rules:
                    if rule.outcome.value == "FALSE" or rule.suggests_review:
                        print(
                            f"  - {rule.rule_kind.value}/{rule.rule_code}: "
                            f"{rule.outcome.value}"
                            f"{' review' if rule.suggests_review else ''}"
                            f" — {rule.summary or ''}"
                        )
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
