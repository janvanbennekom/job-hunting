import pytest

from jobhunter.connectors.undp.client import UndpJobsClient

pytestmark = pytest.mark.live


def test_live_undp_rss() -> None:
    client = UndpJobsClient()
    page = client.fetch_feed()
    assert page.items
    assert page.items[0].get("link")
