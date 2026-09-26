"""Apply curated search strategy seed (Phase 4B)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from jobhunter.domain import (
    ExclusionCriterion,
    RevisionChangeSource,
    SearchTheme,
    StrategyCriterion,
    StrategyCriterionCategory,
    StrategyParameterCode,
)
from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.domain.strategy_content_hash import compute_revision_content_hash
from jobhunter.domain.strategy_criterion_values import parse_criterion_value
from jobhunter.domain.strategy_enums import ExclusionCode, PreferenceStrength
from jobhunter.infrastructure.importers.search_strategy.loader import load_seed
from jobhunter.infrastructure.importers.search_strategy.report import (
    SearchStrategySeedReport,
)
from jobhunter.infrastructure.importers.search_strategy.types import SearchStrategySeed
from jobhunter.infrastructure.importers.search_strategy.validation import validate_seed
from jobhunter.infrastructure.search_strategy.activation_service import (
    SearchStrategyActivationService,
)
from jobhunter.infrastructure.search_strategy.bundle_rebind import (
    finalize_bundle_for_strategy,
)
from jobhunter.infrastructure.search_strategy.identity import (
    exclusion_criterion_id,
    revision_id_for_content,
    search_strategy_id,
    strategy_criterion_id,
    theme_id,
)


class SearchStrategySeeder:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._activation = SearchStrategyActivationService(session)

    def run(self, seed_path: Path, *, apply: bool = False) -> SearchStrategySeedReport:
        seed = load_seed(seed_path)
        report = SearchStrategySeedReport(
            seed_path=str(seed_path.resolve()),
            owner_key=seed.owner_key,
            dry_run=not apply,
            themes_in_seed=len(seed.themes),
            criteria_in_seed=len(seed.criteria),
            exclusions_in_seed=len(seed.exclusions),
        )
        errors = validate_seed(seed)
        report.errors.extend(errors)
        if report.has_errors():
            return report

        bundle = self._build_bundle(seed)
        report.content_hash = compute_revision_content_hash(bundle)
        strategy_id = search_strategy_id(seed.owner_key)
        report.search_strategy_id = strategy_id
        report.revision_id = revision_id_for_content(strategy_id, report.content_hash)

        result = self._activation.activate(
            seed.owner_key,
            bundle,
            change_summary=seed.change_summary,
            change_source=RevisionChangeSource(seed.change_source),
            apply=apply,
        )
        report.no_op = result.no_op
        report.created_new_revision = result.created_new_revision
        report.reactivated_existing_revision = result.reactivated_existing_revision
        report.revision_id = result.revision_id
        if apply and not result.no_op:
            report.applied = True
            self._session.flush()
        return report

    def _build_bundle(self, seed: SearchStrategySeed) -> RevisionContentBundle:
        strategy_id = search_strategy_id(seed.owner_key)
        revision_id = "pending-revision"
        themes: list[SearchTheme] = []
        for row in seed.themes:
            themes.append(
                SearchTheme(
                    id=theme_id(revision_id, row.key),
                    revision_id=revision_id,
                    theme_key=row.key,
                    label=row.label,
                    strength=PreferenceStrength(row.strength),
                    is_active=row.is_active,
                    notes=row.notes,
                    sort_order=row.sort_order,
                )
            )
        criteria: list[StrategyCriterion] = []
        for row in seed.criteria:
            category = StrategyCriterionCategory(row.category)
            code = StrategyParameterCode(row.code)
            criteria.append(
                StrategyCriterion(
                    id=strategy_criterion_id(revision_id, row.category, row.code),
                    revision_id=revision_id,
                    category=category,
                    code=code,
                    value=parse_criterion_value(category, code, row.value),
                    strength=(
                        PreferenceStrength(row.strength)
                        if row.strength is not None
                        else None
                    ),
                    is_active=row.is_active,
                    notes=row.notes,
                    sort_order=row.sort_order,
                )
            )
        exclusions: list[ExclusionCriterion] = []
        for row in seed.exclusions:
            exclusions.append(
                ExclusionCriterion(
                    id=exclusion_criterion_id(revision_id, row.exclusion_code),
                    revision_id=revision_id,
                    exclusion_code=ExclusionCode(row.exclusion_code),
                    parameters=row.parameters,
                    is_active=row.is_active,
                    notes=row.notes,
                )
            )
        partial = RevisionContentBundle(
            themes=tuple(themes),
            criteria=tuple(criteria),
            exclusions=tuple(exclusions),
        )
        rebound, _ = finalize_bundle_for_strategy(strategy_id, partial)
        return rebound
