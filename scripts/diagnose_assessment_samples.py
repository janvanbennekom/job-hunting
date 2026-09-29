"""Read-only: dump stratified production assessment samples (no secrets)."""

from __future__ import annotations

import json
import os
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
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    _load_env(root / ".env")
    sys.path.insert(0, str(root / "src"))
    from sqlalchemy import text

    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    settings = get_settings()
    settings.require_database_url()
    patterns = [
        ("hsse", "%hsse%"),
        ("civil", "%civil engineer%"),
        ("gender", "%gender%"),
        ("gis", "%gis%"),
        ("land", "%land%"),
        ("cadast", "%cadast%"),
    ]
    with session_scope(create_session_factory(create_engine_from_settings(settings))) as s:
        for label, pat in patterns:
            row = s.execute(
                text(
                    """
                    select o.title, a.status, a.model_name, a.validation_warnings,
                           a.result
                    from opportunity_profile_assessments a
                    join opportunities o on o.id = a.opportunity_id
                    where a.model_provider = 'openai'
                      and lower(o.title) like :pat
                    order by a.assessed_at desc
                    limit 1
                    """
                ),
                {"pat": pat},
            ).first()
            print(f"\n=== {label} ===")
            if not row:
                print("(no match)")
                continue
            title, status, model_name, warnings, result = row
            print("title:", title[:100])
            print("status:", status, "model:", model_name)
            print("warnings:", warnings)
            if result:
                data = result if isinstance(result, dict) else json.loads(result)
                print("result keys:", sorted(data.keys()))
                print("overall_relevance:", data.get("overall_relevance"))
                pr = data.get("professional_relevance") or {}
                print("scope_summary len:", len(str(pr.get("scope_summary") or "")))
                print("rationale len:", len(str(data.get("rationale") or "")))
                print("service_alignments:", len(data.get("service_alignments") or []))
        # aggregate: succeeded with empty rationale
        stats = s.execute(
            text(
                """
                select
                  count(*) filter (where status like 'SUCCEEDED%') as ok,
                  count(*) filter (
                    where status like 'SUCCEEDED%'
                    and coalesce(result->>'rationale','') = ''
                  ) as empty_rat,
                  count(*) filter (
                    where status like 'SUCCEEDED%'
                    and result->>'overall_relevance' = 'UNKNOWN'
                  ) as unk
                from opportunity_profile_assessments
                where model_provider = 'openai'
                """
            )
        ).first()
        print("\n=== stats ===", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
