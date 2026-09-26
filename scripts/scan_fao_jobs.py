"""Run an FAO Jobs acquisition scan."""

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
    parser = argparse.ArgumentParser(description="Acquire FAO Jobs vacancies.")
    parser.add_argument(
        "--keyword",
        default="",
        help="Optional FAO keyword search (not persisted as strategy)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum vacancies to retrieve and process",
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

    from jobhunter.application.fao_scan import FaoScanService
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    from jobhunter.domain.source_scan_enums import SourceScanStatus

    if apply:
        get_settings().require_database_url()
        engine = create_engine_from_settings()
        session_factory = create_session_factory(engine)
        try:
            with session_scope(session_factory) as session:
                report = FaoScanService(session).run_scan(
                    keyword=args.keyword or None,
                    limit=args.limit,
                    apply=True,
                )
                for line in report.summary_lines():
                    print(line)
                if report.mapping_errors:
                    print("Mapping errors:")
                    for err in report.mapping_errors:
                        print(f"  - {err}")
                if report.processing_errors:
                    print("Processing errors:")
                    for err in report.processing_errors:
                        print(f"  - {err}")
                return 0 if report.scan.status != SourceScanStatus.FAILED else 1
        finally:
            engine.dispose()
    else:
        from jobhunter.connectors.fao import FaoJobsConnector

        connector = FaoJobsConnector()
        fetch = connector.fetch_requisitions(
            keyword=args.keyword or None, limit=args.limit
        )
        mapping = connector.map_to_raw_opportunities(
            fetch.records,
            source_id="fao-external-jobs",
            scan_id="dry-run",
        )
        print(f"Dry run: retrieved {len(fetch.records)} requisition(s)")
        print(f"Mapped {len(mapping.raw_opportunities)} RawOpportunity object(s)")
        if mapping.errors:
            print("Mapping errors:")
            for err in mapping.errors:
                print(f"  - {err}")
        for raw in mapping.raw_opportunities[:5]:
            print(
                f"  {raw.source_reference}: {raw.raw_title} "
                f"({raw.raw_location})"
            )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
