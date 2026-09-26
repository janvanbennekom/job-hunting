"""Human-readable diff between strategy revision bundles."""

from __future__ import annotations

import json

from jobhunter.application.strategy_conversation.dtos import StrategyDiffLine
from jobhunter.domain.revision_content_bundle import RevisionContentBundle
from jobhunter.domain.strategy_content_hash import canonical_content_payload


def build_strategy_diff(
    current: RevisionContentBundle,
    proposed: RevisionContentBundle,
) -> list[StrategyDiffLine]:
    lines: list[StrategyDiffLine] = []
    current_payload = canonical_content_payload(current)
    proposed_payload = canonical_content_payload(proposed)

    current_themes = {item["theme_key"]: item for item in current_payload["themes"]}
    proposed_themes = {item["theme_key"]: item for item in proposed_payload["themes"]}
    for key in sorted(set(current_themes) | set(proposed_themes)):
        before = current_themes.get(key)
        after = proposed_themes.get(key)
        if before == after:
            continue
        for field in ("strength", "is_active", "notes", "label"):
            b_val = before.get(field) if before else None
            a_val = after.get(field) if after else None
            if b_val != a_val:
                lines.append(
                    StrategyDiffLine(
                        area="theme",
                        item_key=key,
                        field_name=field,
                        current_value=_fmt(b_val),
                        proposed_value=_fmt(a_val),
                    )
                )

    def crit_key(item: dict) -> tuple[str, str]:
        return (item["category"], item["code"])

    current_crit = {crit_key(item): item for item in current_payload["criteria"]}
    proposed_crit = {crit_key(item): item for item in proposed_payload["criteria"]}
    for key in sorted(set(current_crit) | set(proposed_crit)):
        before = current_crit.get(key)
        after = proposed_crit.get(key)
        if before == after:
            continue
        label = f"{key[0]}:{key[1]}"
        lines.append(
            StrategyDiffLine(
                area="criterion",
                item_key=label,
                field_name="value",
                current_value=_fmt(before),
                proposed_value=_fmt(after),
            )
        )

    current_ex = {
        item["exclusion_code"]: item for item in current_payload["exclusions"]
    }
    proposed_ex = {
        item["exclusion_code"]: item for item in proposed_payload["exclusions"]
    }
    for key in sorted(set(current_ex) | set(proposed_ex)):
        before = current_ex.get(key)
        after = proposed_ex.get(key)
        if before == after:
            continue
        for field in ("is_active", "notes"):
            b_val = before.get(field) if before else None
            a_val = after.get(field) if after else None
            if b_val != a_val:
                lines.append(
                    StrategyDiffLine(
                        area="exclusion",
                        item_key=key,
                        field_name=field,
                        current_value=_fmt(b_val),
                        proposed_value=_fmt(a_val),
                    )
                )
    return lines


def _fmt(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)
