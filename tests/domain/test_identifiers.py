"""Tests for domain identifier helpers."""

import uuid

from jobhunter.domain import new_domain_id


def test_new_domain_id_is_uuid_string() -> None:
    value = new_domain_id()
    parsed = uuid.UUID(value)
    assert str(parsed) == value
