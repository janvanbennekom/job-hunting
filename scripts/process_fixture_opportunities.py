"""Process representative raw opportunity fixtures through the Phase 5 pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jobhunter.application.opportunity_processing import OpportunityProcessingService
from jobhunter.domain import JobSource, RawOpportunity
from jobhunter.infrastructure.config import get_settings
from jobhunter.infrastructure.opportunity_processing import FixtureOpportunityNormalizer
from jobhunter.infrastructure.persistence.database import (
    create_engine_from_settings,
    create_session_factory,
    session_scope,
)
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository


def _load_fixture(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("data/fixtures/opportunities/sample_raw_sequence.json"),
    )
    parser.add_argument("--source-id", default="fixture-source")
    parser.add_argument("--source-name", default="Fixture Source")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse fixture only; do not connect to PostgreSQL.",
    )
    args = parser.parse_args(argv)

    items = _load_fixture(args.fixture)
    if args.dry_run:
        print(f"Dry run: {len(items)} raw item(s) in {args.fixture}")
        return 0

    get_settings().require_database_url()
    retrieved = datetime.now(timezone.utc)
    engine = create_engine_from_settings()
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        sources = JobSourceRepository(session)
        source = sources.get_by_id(args.source_id)
        if source is None:
            source = sources.save(
                JobSource(id=args.source_id, name=args.source_name)
            )
        service = OpportunityProcessingService(
            session, FixtureOpportunityNormalizer()
        )
        for index, item in enumerate(items):
            raw = RawOpportunity(
                id=item.get("id", f"fixture-{index}"),
                source_id=source.id,
                retrieved_at=retrieved,
                source_reference=item.get("source_reference"),
                source_url=item.get("source_url"),
                raw_title=item.get("raw_title"),
                raw_organisation=item.get("raw_organisation"),
                raw_location=item.get("raw_location"),
                raw_deadline=item.get("raw_deadline"),
                raw_description=item.get("raw_description"),
                extra=dict(item.get("extra") or {}),
            )
            result = service.process(raw)
            print(
                f"{raw.id} -> opportunity {result.opportunity.id} "
                f"({result.opportunity.lifecycle_status.value})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
