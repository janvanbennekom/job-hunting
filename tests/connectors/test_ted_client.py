"""TED expert query builder tests."""

import re
from datetime import date

from jobhunter.connectors.ted.client import build_ted_expert_query

_LAND_CORE_PHRASES = (
    "land administration",
    "property registration",
    "land registration",
    "land registry",
    "land information system",
    "cadastral survey",
)
_LAND_CORE_UNQUOTED = ("cadastre", "cadastral")
_REMOVED_NOISY = (
    "FT~GIS",
    "FT~SDI",
    "FT~geospatial",
    'FT~"geographic information"',
    'FT~"spatial data"',
    'FT~"digital transformation"',
)


def test_build_query_includes_keyword_and_date_filter() -> None:
    q = build_ted_expert_query(keyword="cadastre", publication_since=date(2025, 1, 1))
    assert 'FT~"cadastre"' in q
    assert "PD>=20250101" in q
    assert "SORT BY publication-date DESC" in q
    assert " OR " not in q.split(" AND ")[0]


def test_default_query_land_core_concepts_present() -> None:
    q = build_ted_expert_query(keyword=None, publication_since=date(2024, 1, 1))
    assert q.startswith("(")
    assert " OR FT~" in q or ' OR FT~"' in q
    for phrase in _LAND_CORE_PHRASES:
        assert f'FT~"{phrase}"' in q
    for term in _LAND_CORE_UNQUOTED:
        assert f"FT~{term}" in q


def test_default_query_excludes_noisy_concepts() -> None:
    q = build_ted_expert_query()
    for fragment in _REMOVED_NOISY:
        assert fragment not in q


def test_default_query_not_malformed_ft_or_inside_single_predicate() -> None:
    q = build_ted_expert_query()
    assert not re.search(r'FT~\([^)]*\bOR\b', q)


def test_default_query_excludes_unrelated_broad_terms() -> None:
    q = build_ted_expert_query().lower()
    for term in ("mapping", "surveying"):
        assert f'ft~"{term}"' not in q
        assert f"ft~{term}" not in q


def test_default_query_publication_date_and_sort() -> None:
    q = build_ted_expert_query(publication_since=date(2024, 6, 15))
    assert "PD>=20240615" in q
    assert "SORT BY publication-date DESC" in q


def test_empty_keyword_uses_default_or_query() -> None:
    q_none = build_ted_expert_query(keyword=None)
    q_blank = build_ted_expert_query(keyword="   ")
    assert q_none == q_blank
    assert "FT~cadastre" in q_none
