"""Tests for JobSource."""

import pytest

from jobhunter.domain import JobSource


def test_job_source_valid_construction() -> None:
    source = JobSource(
        id="src-001",
        name="UNOPS",
        organisation="United Nations",
        url="https://example.org/unops",
        is_active=True,
    )
    assert source.name == "UNOPS"
    assert source.is_active is True


def test_job_source_strips_and_requires_name() -> None:
    source = JobSource(name="  World Bank  ")
    assert source.name == "World Bank"
    assert source.id


def test_job_source_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name"):
        JobSource(name="   ")


def test_job_source_mapping_roundtrip() -> None:
    source = JobSource(id="abc", name="FAO", url="https://fao.org")
    restored = JobSource.from_mapping(source.to_mapping())
    assert restored == source
