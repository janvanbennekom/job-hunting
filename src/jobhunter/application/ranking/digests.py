"""Ranking input digest for idempotency."""

from __future__ import annotations

import hashlib
import json

from jobhunter.domain.ranking_enums import RANKING_METHOD_VERSION


def _sha256_hex(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_ranking_input_digest(
    *,
    opportunity_content_digest: str,
    eligibility_decision_id: str,
    profile_assessment_id: str,
    search_strategy_revision_id: str,
    ranking_method_version: str,
    ranking_config_hash: str,
) -> str:
    payload = {
        "opportunity_content_digest": opportunity_content_digest,
        "eligibility_decision_id": eligibility_decision_id,
        "profile_assessment_id": profile_assessment_id,
        "search_strategy_revision_id": search_strategy_revision_id,
        "ranking_method_version": ranking_method_version,
        "ranking_config_hash": ranking_config_hash,
    }
    return _sha256_hex(payload)


def default_ranking_method_version() -> str:
    return RANKING_METHOD_VERSION


def compute_ranking_state_digest(
    *,
    opportunity_content_digest: str,
    search_strategy_revision_id: str,
    ranking_method_version: str,
    ranking_config_hash: str,
    status: str,
    eligibility_decision_id: str | None,
    profile_assessment_id: str | None,
    reason_code: str | None,
) -> str:
    payload = {
        "opportunity_content_digest": opportunity_content_digest,
        "search_strategy_revision_id": search_strategy_revision_id,
        "ranking_method_version": ranking_method_version,
        "ranking_config_hash": ranking_config_hash,
        "status": status,
        "eligibility_decision_id": eligibility_decision_id,
        "profile_assessment_id": profile_assessment_id,
        "reason_code": reason_code,
    }
    return _sha256_hex(payload)
