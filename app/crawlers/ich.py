from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler
from app.normalizers.dates import parse_date
from app.normalizers.status import normalize_status
from app.normalizers.topics import normalize_topic
from app.storage.models import GuidanceDocument


logger = logging.getLogger(__name__)

ICH_BASE_URL = "https://www.ich.org"
ICH_API_BASE_URL = "https://admin.ich.org"
EFFICACY_PAGE_ALIAS = "/page/efficacy-guidelines"
EFFICACY_PAGE_URL = urljoin(ICH_BASE_URL, EFFICACY_PAGE_ALIAS)
DEADLINE_RE = re.compile(r"Deadline for comments by\s+([^;]+)", re.IGNORECASE)

FetchJson = Callable[[], dict[str, Any]]


class ICHCrawler(BaseCrawler):
    agency = "ICH"
    jurisdiction = "International"

    def __init__(self, fetch_json: FetchJson | None = None) -> None:
        self.fetch_json = fetch_json or fetch_ich_efficacy_page

    def crawl(self) -> list[GuidanceDocument]:
        try:
            return parse_ich_efficacy_payload(self.fetch_json())
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("ICH crawler failed: %s", exc)
            return []


def fetch_ich_efficacy_page() -> dict[str, Any]:
    response = httpx.get(
        f"{ICH_API_BASE_URL}/api/v1/nodes",
        params={"loadEntities[]": "paragraph", "alias": EFFICACY_PAGE_ALIAS},
        headers={
            "Accept": "application/json",
            "Referer": EFFICACY_PAGE_URL,
            "User-Agent": "Mozilla/5.0 reg-guidance-tracker/0.1",
        },
        timeout=60,
        follow_redirects=True,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"ICH API returned {type(payload).__name__}, expected object")
    return payload


def parse_ich_efficacy_payload(payload: dict[str, Any]) -> list[GuidanceDocument]:
    page = _first_page(payload)
    updated_date = _parse_api_datetime(_get(page, "bundleInfo", "updated"))
    documents: list[GuidanceDocument] = []

    for item in _walk_items(page):
        if not _is_guideline_item(item):
            continue
        document = _guideline_to_document(item, updated_date)
        if document is not None:
            documents.append(document)

    return documents


def _guideline_to_document(item: dict[str, Any], updated_date: date | None) -> GuidanceDocument | None:
    code = _clean_text(item.get("code"))
    title = _clean_text(item.get("title"))
    if not code:
        return None
    title = title or code

    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    summary = _html_to_text(item.get("description")) or "Not available."
    comment_end_date = _comment_end_date(details)
    status_raw = _status_raw(item, details)
    full_title = f"ICH {code}" if title == code else f"ICH {code} - {title}"
    status, sub_status = normalize_status(full_title, status_raw, "ICH", comment_end_date=comment_end_date)
    document_url, document_format = _primary_document(item.get("fileGroups"))

    return GuidanceDocument(
        title=full_title,
        agency="ICH",
        jurisdiction="International",
        source_page_url=EFFICACY_PAGE_URL,
        document_url=document_url,
        document_format=document_format,
        published_date=parse_date(details.get("stepDate")),
        updated_date=updated_date,
        comment_end_date=comment_end_date,
        status_raw=status_raw or None,
        status_normalized=status,
        sub_status=sub_status,
        topic_raw="Efficacy",
        topic_normalized=normalize_topic(full_title, "Efficacy", summary),
        product_area="Efficacy",
        summary=summary,
        language="EN",
        reference_number=code,
        needs_manual_review=False,
    )


def _first_page(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise ValueError("ICH API payload does not contain a page item")
    return items[0]


def _walk_items(value: Any, seen: set[int] | None = None) -> list[dict[str, Any]]:
    seen = seen or set()
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        value_id = id(value)
        if value_id in seen:
            return found
        seen.add(value_id)
        found.append(value)
        for child in value.values():
            if isinstance(child, (dict, list)):
                found.extend(_walk_items(child, seen))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_items(child, seen))
    return found


def _is_guideline_item(item: dict[str, Any]) -> bool:
    return bool(item.get("code") and "fileGroups" in item)


def _status_raw(item: dict[str, Any], details: dict[str, Any]) -> str:
    parts = [
        _clean_text(item.get("status")),
        _html_to_text(details.get("infoTitle")) or "",
        _html_to_text(details.get("stepDateLabel")) or "",
    ]
    return " - ".join(part for part in parts if part)


def _comment_end_date(details: dict[str, Any]) -> date | None:
    dates: list[date] = []
    info = details.get("info")
    if not isinstance(info, list):
        return None

    for entry in info:
        if not isinstance(entry, dict):
            continue
        match = DEADLINE_RE.search(str(entry.get("text") or ""))
        if not match:
            continue
        parsed = parse_date(match.group(1).strip())
        if parsed:
            dates.append(parsed)
    return max(dates) if dates else None


def _primary_document(file_groups: Any) -> tuple[str | None, str | None]:
    fallback: tuple[str | None, str | None] = (None, None)
    if not isinstance(file_groups, list):
        return fallback

    groups = sorted(file_groups, key=lambda value: value.get("weight", 0) if isinstance(value, dict) else 0)
    for group in groups:
        if not isinstance(group, dict):
            continue
        files = group.get("files")
        if not isinstance(files, list) or not files:
            continue
        candidate = _file_info(files[0])
        if _clean_text(group.get("title")).lower() == "guideline":
            return candidate
        if fallback[0] is None:
            fallback = candidate
    return fallback


def _file_info(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, dict):
        return None, None
    uri = _clean_text(value.get("uri")) or None
    mimetype = _clean_text(value.get("mimetype")) or None
    return uri, _document_format(mimetype, uri)


def _document_format(mimetype: str | None, uri: str | None) -> str | None:
    text = f"{mimetype or ''} {Path(uri or '').suffix}".lower()
    if "pdf" in text:
        return "PDF"
    if "word" in text or ".docx" in text:
        return "DOCX"
    if "powerpoint" in text or ".ppt" in text:
        return "PPT"
    if "video" in text or ".mp4" in text:
        return "VIDEO"
    return mimetype


def _html_to_text(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _parse_api_datetime(value: Any) -> date | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S%z").date()
    except ValueError:
        return parse_date(text)


def _get(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
