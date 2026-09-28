"""Dashboard and public web URL helpers."""

from __future__ import annotations


def normalize_dashboard_base_url(base_url: str | None) -> str | None:
    """Return base URL for Streamlit under /app (no trailing slash).

    When ``JOBHUNTER_WEB_BASE_URL`` is the site root (e.g. https://jobhunter.example.com),
    ``/app`` is appended. When it already ends with ``/app``, it is preserved.
    """
    if not base_url or not base_url.strip():
        return None
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/app"):
        return normalized
    return f"{normalized}/app"


def build_opportunity_dashboard_url(
    base_url: str | None,
    opportunity_id: str,
) -> str | None:
    """Deep link to the Opportunity detail page in the Streamlit dashboard."""
    base = normalize_dashboard_base_url(base_url)
    if not base:
        return None
    return f"{base}/opportunity_detail?opportunity_id={opportunity_id}"


def parse_opportunity_id_from_query(query: dict[str, str]) -> str | None:
    """Extract opportunity id from URL query parameters."""
    raw = query.get("opportunity_id") or query.get("id")
    if not raw or not str(raw).strip():
        return None
    return str(raw).strip()
