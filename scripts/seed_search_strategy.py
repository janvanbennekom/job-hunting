"""Seed search strategy from curated JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        import os

        os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed search strategy revision from curated JSON."
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=Path("data/seeds/search_strategy_jan_van_bennekom-minnema_uk.json"),
        help="Path to curated search strategy JSON",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes (default: dry-run only)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    if not args.seed.exists():
        print(f"Seed file not found: {args.seed}", file=sys.stderr)
        return 1

    from jobhunter.infrastructure.importers.search_strategy import SearchStrategySeeder
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    engine = create_engine_from_settings()
    session_factory = create_session_factory(engine)
    try:
        with session_scope(session_factory) as session:
            report = SearchStrategySeeder(session).run(args.seed, apply=args.apply)
            for line in report.summary_lines():
                print(line)
            if report.has_errors():
                return 1
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
