"""Dashboard URL helpers."""

from jobhunter.infrastructure.web_urls import (
    build_opportunity_dashboard_url,
    normalize_dashboard_base_url,
    parse_opportunity_id_from_query,
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
    assert url == "https://jobhunter.jvbgis.com/app/opportunity_detail?opportunity_id=opp-123"


def test_parse_opportunity_id_from_query() -> None:
    assert (
        parse_opportunity_id_from_query({"opportunity_id": "abc"})
        == "abc"
    )
    assert parse_opportunity_id_from_query({"id": "legacy"}) == "legacy"
    assert parse_opportunity_id_from_query({}) is None
