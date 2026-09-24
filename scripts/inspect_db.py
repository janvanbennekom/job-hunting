"""Inspect local PostgreSQL (no credentials printed). Run from repo root."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env")
    sys.path.insert(0, str(root / "src"))
    from jobhunter.infrastructure.config import get_settings

    settings = get_settings()
    try:
        url = settings.require_database_url()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar()
        rows = conn.execute(
            text(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                "ORDER BY 1, 2"
            )
        ).fetchall()
        print(f"database={db_name}")
        print(f"user_tables={len(rows)}")
        for schema, name in rows:
            print(f"  {schema}.{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
