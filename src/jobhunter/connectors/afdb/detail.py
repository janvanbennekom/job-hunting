"""Parse public AfDB consultant EOI detail pages."""

from __future__ import annotations

import re
from dataclasses import dataclass

from jobhunter.connectors.developmentaid.html_text import html_to_plain_text

_CLOSING_DATE = re.compile(
    r"Closing date:\s*</span>\s*<span class=\"field-content\">([^<]+)</span>",
    re.IGNORECASE,
)
_META_DESCRIPTION = re.compile(
    r'<meta name="description" content="([^"]+)"',
    re.IGNORECASE,
)
_FIELD_BODY = re.compile(
    r'<div class="field-item even">(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)


@dataclass(slots=True)
class AfdbDetailPage:
    closing_date: str | None = None
    meta_description: str | None = None
    body_text: str | None = None


def parse_afdb_detail_html(html: str) -> AfdbDetailPage:
    closing = None
    match = _CLOSING_DATE.search(html)
    if match:
        closing = match.group(1).strip()

    meta = None
    meta_match = _META_DESCRIPTION.search(html)
    if meta_match:
        meta = meta_match.group(1).strip()

    body = None
    body_match = _FIELD_BODY.search(html)
    if body_match:
        body = html_to_plain_text(body_match.group(1))

    return AfdbDetailPage(
        closing_date=closing,
        meta_description=meta,
        body_text=body,
    )
