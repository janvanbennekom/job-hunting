import pytest

from jobhunter.connectors.afdb.client import AfdbConsultantsClient

pytestmark = pytest.mark.live


def test_live_afdb_rss() -> None:
    client = AfdbConsultantsClient()
    page = client.fetch_feed()
    assert page.items
    assert page.items[0].get("guid")
