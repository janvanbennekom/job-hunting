"""Repositories for opportunity rankings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.opportunity_ranking import OpportunityRanking
from jobhunter.domain.ranking_enums import RankingStatus
from jobhunter.infrastructure.persistence import ranking_mappers as mappers
from jobhunter.infrastructure.persistence.models import OpportunityRankingRow


class OpportunityRankingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: OpportunityRanking) -> OpportunityRanking:
        row = mappers.ranking_to_row(entity)
        self._session.add(row)
        self._session.flush()
        return mappers.ranking_to_domain(row)

    def get_by_id(self, entity_id: str) -> OpportunityRanking | None:
        row = self._session.get(OpportunityRankingRow, entity_id)
        if row is None:
            return None
        return mappers.ranking_to_domain(row)

    def list_for_opportunity(self, opportunity_id: str) -> list[OpportunityRanking]:
        stmt = (
            select(OpportunityRankingRow)
            .where(OpportunityRankingRow.opportunity_id == opportunity_id)
            .order_by(OpportunityRankingRow.ranked_at)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.ranking_to_domain(row) for row in rows]

    def find_reusable_by_digest(
        self, opportunity_id: str, input_digest: str
    ) -> OpportunityRanking | None:
        stmt = (
            select(OpportunityRankingRow)
            .where(
                OpportunityRankingRow.opportunity_id == opportunity_id,
                OpportunityRankingRow.input_digest == input_digest,
            )
            .order_by(OpportunityRankingRow.ranked_at.desc())
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.ranking_to_domain(row)

    def find_current_ranked_for_revision(
        self, opportunity_id: str, revision_id: str
    ) -> OpportunityRanking | None:
        stmt = (
            select(OpportunityRankingRow)
            .where(
                OpportunityRankingRow.opportunity_id == opportunity_id,
                OpportunityRankingRow.search_strategy_revision_id == revision_id,
                OpportunityRankingRow.status == RankingStatus.RANKED.value,
            )
            .order_by(OpportunityRankingRow.ranked_at.desc())
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.ranking_to_domain(row)

    def list_for_opportunity_and_revision(
        self, opportunity_id: str, revision_id: str
    ) -> list[OpportunityRanking]:
        stmt = (
            select(OpportunityRankingRow)
            .where(
                OpportunityRankingRow.opportunity_id == opportunity_id,
                OpportunityRankingRow.search_strategy_revision_id == revision_id,
            )
            .order_by(OpportunityRankingRow.ranked_at.desc())
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.ranking_to_domain(row) for row in rows]

    def get_latest_for_opportunity_and_revision(
        self, opportunity_id: str, revision_id: str
    ) -> OpportunityRanking | None:
        rankings = self.list_for_opportunity_and_revision(
            opportunity_id, revision_id
        )
        return rankings[0] if rankings else None
