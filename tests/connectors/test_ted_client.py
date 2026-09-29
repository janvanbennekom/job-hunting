"""TED expert query builder tests."""

from datetime import date

from jobhunter.connectors.ted.client import build_ted_expert_query


def test_build_query_includes_keyword_and_date_filter() -> None:
    q = build_ted_expert_query(keyword="cadastre", publication_since=date(2025, 1, 1))
    assert 'FT~"cadastre"' in q
    assert "PD>=20250101" in q
