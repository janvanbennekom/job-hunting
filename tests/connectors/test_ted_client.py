"""TED expert query builder tests."""

import re
from datetime import date

from jobhunter.connectors.ted.client import build_ted_expert_query


def test_build_query_includes_keyword_and_date_filter() -> None:
    q = build_ted_expert_query(keyword="cadastre", publication_since=date(2025, 1, 1))
    assert 'FT~"cadastre"' in q
    assert "PD>=20250101" in q
    assert "SORT BY publication-date DESC" in q
    assert " OR " not in q.split(" AND ")[0]


def test_default_query_uses_separate_ft_predicates_or_joined() -> None:
    q = build_ted_expert_query(keyword=None, publication_since=date(2024, 1, 1))
    assert q.startswith("(")
    assert " OR FT~" in q or " OR FT~\"" in q
    assert 'FT~"land administration"' in q
    assert "FT~cadastre" in q
    assert "FT~cadastral" in q
    assert "FT~geospatial" in q
    assert 'FT~"geographic information"' in q
    assert 'FT~"spatial data"' in q
    assert "FT~GIS" in q
    assert "FT~SDI" in q
    assert 'FT~"digital transformation"' in q
    assert 'FT~"property registration"' in q


def test_default_query_not_malformed_ft_or_inside_single_predicate() -> None:
    q = build_ted_expert_query()
    assert not re.search(r'FT~\([^)]*\bOR\b', q)


def test_default_query_excludes_overly_broad_terms() -> None:
    q = build_ted_expert_query().lower()
    for term in (
        "information system",
        "registry",
        "mapping",
        "surveying",
        "land information system",
    ):
        assert term not in q


def test_default_query_publication_date_and_sort() -> None:
    q = build_ted_expert_query(publication_since=date(2024, 6, 15))
    assert "PD>=20240615" in q
    assert "SORT BY publication-date DESC" in q


def test_empty_keyword_uses_default_or_query() -> None:
    q_none = build_ted_expert_query(keyword=None)
    q_blank = build_ted_expert_query(keyword="   ")
    assert q_none == q_blank
    assert "FT~cadastre" in q_none
