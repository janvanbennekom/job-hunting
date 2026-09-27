"""Minimal HTML to plain text for job descriptions."""

from __future__ import annotations

import re
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)


def html_to_plain_text(html: str | None) -> str | None:
    if html is None:
        return None
    stripped = html.strip()
    if not stripped:
        return None
    parser = _TextExtractor()
    parser.feed(stripped)
    text = parser.text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() or None
