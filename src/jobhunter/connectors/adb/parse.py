"""Parse ADB CSRN Oracle HTML listing pages."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from jobhunter.connectors.adb.identity import ADB_CSRN_LISTING_URL

NOTICE_ID_RE = re.compile(r"E-\d{6}-\d{3}")
LISTING_MARKER = "CMS Consulting Opportunities"
ROW_PROJECT_PREFIX = "atResults:mstProject:"
LISTING_FALLBACK_MARKER = "atResults:imgCsrn:"


class AdbCsrnParseError(ValueError):
    """Listing HTML could not be parsed (layout or session failure)."""


@dataclass(slots=True)
class AdbCsrnNotice:
    notice_id: str
    title: str
    expertise: str | None
    consultant_type: str | None
    published: str | None
    deadline: str | None
    duration_months: str | None
    project_url: str | None
    project_number: str | None
    country_code: str | None
    row_index: int

    def to_record(self) -> dict[str, Any]:
        return {
            "notice_id": self.notice_id,
            "title": self.title,
            "expertise": self.expertise,
            "consultant_type": self.consultant_type,
            "published": self.published,
            "deadline": self.deadline,
            "duration_months": self.duration_months,
            "project_url": self.project_url,
            "project_number": self.project_number,
            "country_code": self.country_code,
            "row_index": self.row_index,
            "listing_url": listing_notice_url(self.notice_id),
        }


def listing_notice_url(notice_id: str) -> str:
    return f"{ADB_CSRN_LISTING_URL}#notice={notice_id}"


def extract_notice_id(title: str) -> str | None:
    match = NOTICE_ID_RE.search(title)
    return match.group(0) if match else None


def extract_country_code(title: str) -> str | None:
    """Parse ISO-like country token after financing instrument (e.g. 'UZB:')."""
    match = re.search(
        r"(?:LOAN|GRANT|TA)(?:\s+E-\d{6}-\d{3})?\s+([A-Z]{3}):",
        title,
        re.I,
    )
    if match:
        return match.group(1).upper()
    match = re.search(r"\b([A-Z]{3}):\s", title)
    return match.group(1).upper() if match else None


def extract_project_number(project_url: str | None) -> str | None:
    if not project_url:
        return None
    match = re.search(r"/projects/(\d+-\d+)/", project_url)
    return match.group(1) if match else None


class _FormFieldParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}
        self.form_action: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        if tag == "form" and ad.get("name") == "DefaultFormName":
            self.form_action = ad.get("action")
        if tag == "input" and ad.get("name"):
            self.fields[ad["name"]] = ad.get("value", "")


def parse_form_fields(page_html: str) -> tuple[str | None, dict[str, str]]:
    parser = _FormFieldParser()
    parser.feed(page_html)
    return parser.form_action, parser.fields


def extract_next_page_tokens(page_html: str) -> tuple[str, str] | None:
    match = re.search(
        r'title="Next 25"[^>]*onclick="_navBarSubmit\(\'DefaultFormName\', '
        r"'goto','atResults',1,'([^']+)','([^']+)'",
        page_html,
    )
    if not match:
        return None
    return match.group(1), match.group(2)


def _span_text(page_html: str, field: str, index: int) -> str | None:
    pattern = (
        rf'id="atResults:{field}:{index}"[^>]*>(.*?)</td>'
    )
    match = re.search(pattern, page_html, re.I | re.S)
    if not match:
        return None
    cell = match.group(1)
    inner = re.sub(r"<[^>]+>", " ", cell)
    text = html.unescape(re.sub(r"\s+", " ", inner)).strip()
    return text or None


def _project_row(page_html: str, index: int) -> tuple[str, str, str] | None:
    match = re.search(
        rf'id="atResults:mstProject:{index}"[^>]*title="([^"]*)"[^>]*href="([^"]*)"[^>]*>'
        rf"([^<]*)</a>",
        page_html,
        re.I | re.S,
    )
    if not match:
        return None
    title_attr = html.unescape(match.group(1)).strip()
    href = html.unescape(match.group(2)).strip()
    link_text = html.unescape(re.sub(r"\s+", " ", match.group(3))).strip()
    title = title_attr or link_text
    return title, href, title


def _row_indices(page_html: str) -> list[int]:
    indices = sorted(
        {
            int(m.group(1))
            for m in re.finditer(r"atResults:mstProject:(\d+)", page_html)
        }
    )
    return indices


def parse_listing_page(page_html: str) -> list[AdbCsrnNotice]:
    if (
        LISTING_MARKER not in page_html
        and ROW_PROJECT_PREFIX not in page_html
        and LISTING_FALLBACK_MARKER not in page_html
    ):
        raise AdbCsrnParseError("ADB CSRN listing marker not found in response")
    if ROW_PROJECT_PREFIX not in page_html:
        return []

    notices: list[AdbCsrnNotice] = []
    for index in _row_indices(page_html):
        project = _project_row(page_html, index)
        if not project:
            continue
        title, project_url, _ = project
        notice_id = extract_notice_id(title)
        if not notice_id:
            continue
        consultant_raw = _span_text(page_html, "mcConsType", index)
        notices.append(
            AdbCsrnNotice(
                notice_id=notice_id,
                title=title,
                expertise=_span_text(page_html, "mstExpertise2", index),
                consultant_type=consultant_raw,
                published=_span_text(page_html, "mstPublished", index),
                deadline=_span_text(page_html, "mstDeadline", index),
                duration_months=_span_text(page_html, "mstDuration1", index),
                project_url=project_url or None,
                project_number=extract_project_number(project_url),
                country_code=extract_country_code(title),
                row_index=index,
            )
        )

    if ROW_PROJECT_PREFIX in page_html and not notices:
        raise AdbCsrnParseError(
            "ADB CSRN listing rows present but no notices could be parsed"
        )
    return notices
