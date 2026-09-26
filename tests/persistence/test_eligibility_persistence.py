"""Integration tests for eligibility persistence and re-evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.domain import LifecycleStatus, Opportunity
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.eligibility_repositories import (
    EligibilityRuleResultRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
)

pytestmark = pytest.mark.integration


def test_persist_decision_and_rules(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="elig-test-opp-001",
            title="Land administration consultant",
            lifecycle_status=LifecycleStatus.NEW,
        )
    )
    service = EligibilityFilterService(db_session)
    snapshot = service.resolve_active_snapshot(PRIMARY_PROFILE_KEY)
    result = service.evaluate_and_persist(opp.id)
    assert result.decision.search_strategy_revision_id == snapshot.revision.id
    rules = EligibilityRuleResultRepository(db_session).list_for_decision(
        result.decision.id
    )
    assert len(rules) >= 1
    loaded = opportunities.get_by_id(opp.id)
    assert loaded is not None
    assert loaded.eligibility_status == result.decision.status


def test_re_evaluation_retains_history(db_session: Session) -> None:
    opportunities = OpportunityRepository(db_session)
    opp = opportunities.save(
        Opportunity(
            id="elig-test-opp-002",
            title="Internship Programme Coordinator",
            description="Internship programme for graduates.",
            lifecycle_status=LifecycleStatus.NEW,
        )
    )
    service = EligibilityFilterService(db_session)
    first = service.evaluate_and_persist(opp.id)
    second = service.evaluate_and_persist(opp.id)
    decisions = service.list_decisions_for_opportunity(opp.id)
    assert len(decisions) == 2
    assert first.decision.id != second.decision.id
    loaded = opportunities.get_by_id(opp.id)
    assert loaded is not None
    assert loaded.eligibility_status == second.decision.status
    assert second.decision.status.value == "INELIGIBLE"


def test_fao_scan_integration_runs_eligibility(
    db_session: Session,
) -> None:
    from jobhunter.application.fao_scan import FaoScanService
    from jobhunter.connectors.fao.connector import FaoJobsConnector, FaoScanResult
    from tests.persistence.test_fao_scan_integration import _FixtureFaoConnector
    import json
    from pathlib import Path

    payload = json.loads(
        Path("tests/fixtures/fao/searchjobs_sample.json").read_text(encoding="utf-8")
    )
    service = FaoScanService(db_session, _FixtureFaoConnector(payload["requisitionList"][:1]))
    report = service.run_scan(limit=1, apply=True)
    assert report.processed == 1
    strategies = SearchStrategyRepository(db_session)
    strategy = strategies.get_by_owner_key(PRIMARY_PROFILE_KEY)
    assert strategy is not None
    assert strategy.current_revision_id is not None
