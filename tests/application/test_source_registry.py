"""Source registry extensibility tests."""

from jobhunter.application.sources.registry import (
    connector_meta_for_key,
    list_registered_connectors,
    registered_source_keys,
)


def test_registry_lists_known_connectors() -> None:
    keys = {item.source_key for item in list_registered_connectors()}
    assert keys == registered_source_keys()
    assert connector_meta_for_key("fao") is not None
    assert connector_meta_for_key("unknown") is None
