"""Run a DevelopmentAid Jobs acquisition scan."""

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
    parser = argparse.ArgumentParser(description="Acquire DevelopmentAid job vacancies.")
    parser.add_argument(
        "--keyword",
        default="",
        help="Optional keyword filter (not persisted as strategy)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum vacancies to retrieve and process",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip per-job detail API calls (list summary only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and map only; do not write to PostgreSQL",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist scan results and process through Phase 5 pipeline",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    apply = args.apply and not args.dry_run
    if not args.dry_run and not args.apply:
        print(
            "Specify --dry-run to inspect retrieval or --apply to persist results.",
            file=sys.stderr,
        )
        return 1

    from jobhunter.application.developmentaid_scan import DevelopmentAidScanService
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    if apply:
        get_settings().require_database_url()
        engine = create_engine_from_settings()
        session_factory = create_session_factory(engine)
        try:
            with session_scope(session_factory) as session:
                report = DevelopmentAidScanService(session).run_scan(
                    keyword=args.keyword or None,
                    limit=args.limit,
                    apply=True,
                    fetch_details=not args.no_details,
                )
                for line in report.summary_lines():
                    print(line)
                if report.mapping_errors:
                    print("Mapping errors:", len(report.mapping_errors))
                if report.processing_errors:
                    print("Processing errors:", len(report.processing_errors))
            return 0
        finally:
            engine.dispose()

    from jobhunter.connectors.developmentaid.connector import DevelopmentAidJobsConnector
    from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_SOURCE_ID

    connector = DevelopmentAidJobsConnector()
    fetch = connector.fetch_jobs(
        keyword=args.keyword or None,
        limit=args.limit,
        fetch_details=not args.no_details,
    )
    mapping = connector.map_to_raw_opportunities(
        fetch,
        source_id=DEVELOPMENTAID_JOBS_SOURCE_ID,
        scan_id="dry-run",
    )
    print(f"Dry-run retrieved: {len(fetch.records)}")
    print(f"Mapped raw opportunities: {len(mapping.raw_opportunities)}")
    for raw in mapping.raw_opportunities[:5]:
        desc_len = len(raw.raw_description or "")
        print(
            f"  {raw.source_reference} | {raw.raw_title[:60]} | desc_chars={desc_len}"
        )
    if mapping.errors:
        print("Errors:", mapping.errors[:3])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
