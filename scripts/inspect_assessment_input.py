"""Reconstruct assessment request payload size for one opportunity (read-only)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    for line in (root / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            os.environ.setdefault(*line.split("=", 1))
    sys.path.insert(0, str(root / "src"))

    from sqlalchemy import text

    from jobhunter.ai.fake_model import FakeAssessmentModel
    from jobhunter.application.profile_assessment.service import (
        OpportunityProfileAssessmentService,
    )
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    settings = get_settings()
    settings.require_database_url()
    with session_scope(create_session_factory(create_engine_from_settings(settings))) as s:
        opp_id = s.execute(
            text(
                "select a.opportunity_id from opportunity_profile_assessments a "
                "join opportunities o on o.id = a.opportunity_id "
                "where lower(o.title) = 'civil engineer' limit 1"
            )
        ).scalar()
        if not opp_id:
            print("no civil engineer")
            return 1
        svc = OpportunityProfileAssessmentService(s, FakeAssessmentModel())
        outcome = svc.assess_opportunity(opp_id, dry_run=True)
        req = outcome.assessment.result["request"]
        pack = req["evidence_pack"]
        print("opportunity_id", opp_id)
        print("services", len(pack.get("professional_services", [])))
        print("assignments", len(pack.get("assignments", [])))
        print("capabilities", len(pack.get("capabilities", [])))
        print("skills", len(pack.get("skills", [])))
        opt = req["opportunity_prompt_text"]
        print("title len", len(opt.get("TITLE", "")))
        print("description len", len(opt.get("DESCRIPTION", "")))
        print("sufficiency", req["source_data_sufficiency"])
        print("instructions", req.get("instructions", "")[:120])
        print("themes", len(req.get("search_themes", [])))
        payload = json.dumps(req, ensure_ascii=False)
        print("request_json_chars", len(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
