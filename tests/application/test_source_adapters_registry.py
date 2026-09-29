"""Source adapter registry tests."""

from jobhunter.application.automation.source_adapters import default_source_adapters


def test_default_adapters_include_phase_17b_sources() -> None:
    adapters = default_source_adapters()
    assert set(adapters) == {
        "fao",
        "developmentaid",
        "worldbank",
        "undp",
        "afdb",
        "adb",
        "reliefweb",
        "ted",
    }
