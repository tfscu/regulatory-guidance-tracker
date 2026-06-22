from __future__ import annotations

import logging
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

CDE_GUIDANCE_URL = (
    "https://www.cde.org.cn/zdyz/listpage/9cd8db3b7530c6fa0c86485e563f93c7"
    "?isHomePage=true"
)
CDE_BASE_URL = "https://www.cde.org.cn"
CDE_ALLOWED_PRODUCT_AREAS = ("化学药", "生物制品")

FetchText = Callable[[], str]


class CDECrawler(BaseCrawler):
    agency = "CDE"
    jurisdiction = "China"

    def __init__(self, fetch_text: FetchText | None = None) -> None:
        self.fetch_text = fetch_text or fetch_cde_guidance_page

    def crawl(self) -> list[GuidanceDocument]:
        try:
            return parse_cde_guidance_html(self.fetch_text())
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("CDE crawler failed: %s", exc)
            return []


def fetch_cde_guidance_page() -> str:
    response = httpx.get(
        CDE_GUIDANCE_URL,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Referer": "https://www.cde.org.cn/",
            "User-Agent": "Mozilla/5.0 reg-guidance-tracker/0.1",
        },
        timeout=60,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def parse_cde_guidance_html(html: str) -> list[GuidanceDocument]:
    if _looks_like_protection_page(html):
        raise ValueError("CDE returned a protection page instead of guidance content")

    soup = BeautifulSoup(html, "html.parser")
    documents: list[GuidanceDocument] = []
    for row in soup.select("tr"):
        document = _row_to_document(row)
        if document is not None:
            documents.append(document)
    return documents


def parse_cde_guidance_items(items: list[dict[str, Any]]) -> list[GuidanceDocument]:
    return [document for item in items if (document := _item_to_document(item)) is not None]


def _row_to_document(row: Any) -> GuidanceDocument | None:
    cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
    if len(cells) < 2:
        return None
    link = row.find("a", href=True)
    if link is None:
        return None
    title = _clean_text(link.get_text(" ", strip=True)) or cells[0]
    if not title or "指导原则" not in title:
        return None
    return _build_document(
        title=title,
        source_page_url=urljoin(CDE_BASE_URL, link["href"]),
        published_date=_first_parseable_date(cells),
        product_area=_first_matching_area(cells),
        summary="Not available.",
    )


def _item_to_document(item: dict[str, Any]) -> GuidanceDocument | None:
    title = _first_value(item, "title", "name", "bt", "noticeTitle", "guideName")
    if not title or "指导原则" not in title:
        return None

    product_area = _first_value(item, "productArea", "drugType", "scope", "适用范围")
    if product_area and not any(area in product_area for area in CDE_ALLOWED_PRODUCT_AREAS):
        return None

    return _build_document(
        title=title,
        source_page_url=urljoin(CDE_BASE_URL, _first_value(item, "url", "href", "link", "source_page_url")),
        document_url=urljoin(CDE_BASE_URL, _first_value(item, "document_url", "fileUrl", "attachmentUrl")),
        published_date=parse_date(_first_value(item, "published_date", "publishDate", "date", "发布日期")),
        updated_date=parse_date(_first_value(item, "updated_date", "updateDate")),
        product_area=product_area or None,
        summary=_first_value(item, "summary", "content", "description") or "Not available.",
    )


def _build_document(
    *,
    title: str,
    source_page_url: str,
    published_date: Any = None,
    updated_date: Any = None,
    product_area: str | None = None,
    summary: str = "Not available.",
    document_url: str | None = None,
) -> GuidanceDocument:
    document_url = document_url or None
    status, sub_status = normalize_status(title, None, "CDE")
    return GuidanceDocument(
        title=title,
        agency="CDE",
        jurisdiction="China",
        source_page_url=source_page_url or CDE_GUIDANCE_URL,
        document_url=document_url,
        document_format=_document_format(document_url),
        published_date=published_date if hasattr(published_date, "year") else parse_date(published_date),
        updated_date=updated_date if hasattr(updated_date, "year") else parse_date(updated_date),
        status_normalized=status,
        sub_status=sub_status,
        topic_raw=product_area,
        topic_normalized=normalize_topic(title, product_area, summary),
        product_area=product_area,
        summary=summary or "Not available.",
        language="ZH",
        needs_manual_review=False,
    )


def _looks_like_protection_page(html: str) -> bool:
    text = html[:5000]
    return "9DhefwqGPrzGxEp9hPaoag" in text or "$_ts" in text


def _first_value(item: dict[str, Any], *keys: str) -> str:
    lowered = {str(key).lower(): value for key, value in item.items()}
    for key in keys:
        value = item.get(key)
        if value is None:
            value = lowered.get(key.lower())
        text = _clean_text(value)
        if text:
            return text
    return ""


def _first_parseable_date(values: list[str]):
    for value in values:
        parsed = parse_date(value)
        if parsed:
            return parsed
    return None


def _first_matching_area(values: list[str]) -> str | None:
    for value in values:
        for area in CDE_ALLOWED_PRODUCT_AREAS:
            if area in value:
                return area
    return None


def _document_format(url: str | None) -> str | None:
    if not url:
        return None
    lowered = url.lower()
    if lowered.endswith(".pdf"):
        return "PDF"
    if lowered.endswith((".doc", ".docx")):
        return "DOCX"
    return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())
