from pathlib import Path

from jobhunter.connectors.rss_feed import parse_rss_items


def test_parse_undp_fixture_items() -> None:
    xml_bytes = Path("tests/fixtures/undp/rss_sample.xml").read_bytes()
    items = parse_rss_items(xml_bytes)
    assert len(items) == 3
    assert "GIS Specialist" in (items[0].get("title") or "")
