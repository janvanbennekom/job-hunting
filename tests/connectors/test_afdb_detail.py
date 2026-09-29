from pathlib import Path

from jobhunter.connectors.afdb.detail import parse_afdb_detail_html


def test_parse_closing_date_and_body() -> None:
    html = Path("tests/fixtures/afdb/detail_page_sample.html").read_text(
        encoding="utf-8"
    )
    detail = parse_afdb_detail_html(html)
    assert detail.closing_date == "16-Oct-2026"
    assert detail.body_text
    assert detail.meta_description
