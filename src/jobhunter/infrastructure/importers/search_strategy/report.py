"""Search strategy seed run report."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SearchStrategySeedReport:
    seed_path: str
    owner_key: str
    content_hash: str | None = None
    dry_run: bool = True
    applied: bool = False
    no_op: bool = False
    created_new_revision: bool = False
    reactivated_existing_revision: bool = False
    revision_id: str | None = None
    search_strategy_id: str | None = None
    themes_in_seed: int = 0
    criteria_in_seed: int = 0
    exclusions_in_seed: int = 0
    errors: list[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        return bool(self.errors)

    def summary_lines(self) -> list[str]:
        lines = [
            f"Seed: {self.seed_path}",
            f"Owner: {self.owner_key}",
            f"Content hash: {self.content_hash}",
            f"Mode: {'dry-run' if self.dry_run else 'apply'}",
            "",
            "Input:",
            f"  Themes: {self.themes_in_seed}",
            f"  Criteria: {self.criteria_in_seed}",
            f"  Exclusions: {self.exclusions_in_seed}",
            "",
            "Outcome:",
            f"  no_op: {self.no_op}",
            f"  created_new_revision: {self.created_new_revision}",
            f"  reactivated_existing_revision: {self.reactivated_existing_revision}",
            f"  revision_id: {self.revision_id}",
        ]
        if self.errors:
            lines.extend(["", f"Errors ({len(self.errors)}):"])
            lines.extend(f"  - {e}" for e in self.errors)
        return lines
