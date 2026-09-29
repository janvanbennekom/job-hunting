from pathlib import Path

from jobhunter.connectors.undp.client import UndpJobsClient


class _FixtureUndpClient(UndpJobsClient):
    def fetch_feed(self):
        from jobhunter.connectors.undp.client import UndpFeedPage
        from jobhunter.connectors.rss_feed import parse_rss_items

        xml_bytes = Path("tests/fixtures/undp/rss_sample.xml").read_bytes()
        return UndpFeedPage(items=parse_rss_items(xml_bytes))


def test_fetch_feed_from_fixture() -> None:
    client = _FixtureUndpClient()
    page = client.fetch_feed()
    assert len(page.items) == 3
