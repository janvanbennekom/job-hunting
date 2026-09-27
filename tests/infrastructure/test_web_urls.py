"""Dashboard URL helpers."""

from jobhunter.infrastructure.web_urls import (
    build_opportunity_dashboard_url,
    normalize_dashboard_base_url,
)


def test_normalize_appends_app_path() -> None:
    assert (
        normalize_dashboard_base_url("https://jobhunter.example.com")
        == "https://jobhunter.example.com/app"
    )


def test_normalize_preserves_existing_app() -> None:
    assert (
        normalize_dashboard_base_url("https://jobhunter.example.com/app")
        == "https://jobhunter.example.com/app"
    )


def test_build_opportunity_dashboard_url() -> None:
    url = build_opportunity_dashboard_url(
        "https://jobhunter.jvbgis.com",
        "opp-123",
    )
    assert url == "https://jobhunter.jvbgis.com/app/?opportunity_id=opp-123"
