"""Read models for source management UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceOperationalRow:
    source_key: str
    display_name: str
    connector_label: str
    job_source_id: str
    configured: bool
    enabled: bool
    keyword: str
    limit: int
    fetch_details: bool
    last_scan_started_at: str | None
    last_scan_finished_at: str | None
    last_scan_status: str | None
    last_error_summary: str | None
    records_retrieved: int | None
    records_failed: int | None
    opportunity_link_count: int
