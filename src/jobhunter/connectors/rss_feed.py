"""Minimal RSS/RDF feed parsing for public vacancy feeds."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _text(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    text = (element.text or "").strip()
    if text:
        return text
    if len(element):
        combined = "".join(element.itertext()).strip()
        return combined or None
    return None


def parse_rss_items(xml_bytes: bytes) -> list[dict[str, Any]]:
    """
    Parse RSS 0.9x/2.x or RDF items into a normalized list of dicts.

    Each item contains: title, link, description, pub_date, guid, creator.
    """
    root = ET.fromstring(xml_bytes)
    items: list[dict[str, Any]] = []

    for element in root.iter():
        if _local_name(element.tag) != "item":
            continue
        child_map: dict[str, ET.Element] = {}
        for child in element:
            child_map[_local_name(child.tag)] = child
        creator = None
        for child in element:
            if _local_name(child.tag) == "creator":
                creator = _text(child)
                break
        items.append(
            {
                "title": _text(child_map.get("title")),
                "link": _text(child_map.get("link")),
                "description": _text(child_map.get("description")),
                "pub_date": _text(child_map.get("pubDate")),
                "guid": _text(child_map.get("guid")),
                "creator": creator,
            }
        )
    return items
