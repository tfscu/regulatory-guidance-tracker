from __future__ import annotations

import logging
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

CDE_GUIDANCE_URL = (
    "https://www.cde.org.cn/zdyz/listpage/9cd8db3b7530c6fa0c86485e563f93c7"
    "?isHomePage=true"
)
CDE_BASE_URL = "https://www.cde.org.cn"
CDE_ALLOWED_PRODUCT_AREAS = ("化学药", "生物制品")
DEFAULT_PAGE_SIZE = 100
EDGE_PATHS = (
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
)

FetchText = Callable[[], str]
FetchItems = Callable[[], list[dict[str, Any]]]


class CDECrawler(BaseCrawler):
    agency = "CDE"
    jurisdiction = "China"

    def __init__(self, fetch_text: FetchText | None = None, fetch_items: FetchItems | None = None) -> None:
        self.fetch_text = fetch_text or fetch_cde_guidance_page
        self.fetch_items = fetch_items or fetch_cde_guidance_items_with_browser

    def crawl(self) -> list[GuidanceDocument]:
        try:
            items = self.fetch_items()
            if items:
                return parse_cde_guidance_items(items)
            return parse_cde_guidance_html(self.fetch_text())
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("CDE crawler failed: %s", exc)
            return []
        except ImportError as exc:
            logger.warning("CDE browser crawler requires playwright: %s", exc)
            return []


def fetch_cde_guidance_items_with_browser() -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        launch_kwargs: dict[str, Any] = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        }
        edge_path = _edge_executable_path()
        if edge_path is not None:
            launch_kwargs["executable_path"] = str(edge_path)

        browser = playwright.chromium.launch(**launch_kwargs)
        try:
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
                ),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                viewport={"width": 1365, "height": 900},
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            page = context.new_page()
            page.goto(CDE_GUIDANCE_URL, wait_until="networkidle", timeout=90_000)
            page.wait_for_timeout(1000)
            items = page.evaluate(
                """
                async ({ areas, pageSize }) => {
                  function post(payload) {
                    return new Promise((resolve, reject) => {
                      window.$.ajax({
                        url: window.getRootPath() + '/getDomesticGuideList',
                        type: 'post',
                        data: payload,
                        success: resolve,
                        error: xhr => reject(new Error('CDE list request failed: ' + xhr.status))
                      });
                    });
                  }

                  const records = [];
                  for (const area of areas) {
                    const first = await post({
                      pageNum: 1,
                      pageSize,
                      searchTitle: '',
                      zyfl1: area,
                      zyfl2: '',
                      issueDate1: '',
                      issueDate2: ''
                    });
                    if (!first || first.code !== 200 || !first.data) {
                      continue;
                    }
                    records.push(...(first.data.records || []));
                    const pages = Number(first.data.pages || 1);
                    for (let pageNum = 2; pageNum <= pages; pageNum += 1) {
                      const next = await post({
                        pageNum,
                        pageSize,
                        searchTitle: '',
                        zyfl1: area,
                        zyfl2: '',
                        issueDate1: '',
                        issueDate2: ''
                      });
                      if (next && next.code === 200 && next.data && Array.isArray(next.data.records)) {
                        records.push(...next.data.records);
                      }
                    }
                  }
                  return records;
                }
                """,
                {"areas": list(CDE_ALLOWED_PRODUCT_AREAS), "pageSize": DEFAULT_PAGE_SIZE},
            )
            if not isinstance(items, list):
                raise ValueError("CDE browser crawler did not return a list")
            deduped_items = _dedupe_items([item for item in items if isinstance(item, dict)])
            return _enrich_items_with_detail_links(context, deduped_items)
        finally:
            browser.close()


def _edge_executable_path() -> Path | None:
    return next((path for path in EDGE_PATHS if path.exists()), None)


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


def extract_cde_attachment_from_html(html: str, base_url: str = CDE_BASE_URL) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one('a[href*="downloadAtt"]')
    if link is None or not link.get("href"):
        return None, None
    attachment_text = _clean_text(link.get_text(" ", strip=True))
    attachment_url = urljoin(base_url, link["href"])
    return attachment_url, _document_format(attachment_url, attachment_text)


def _row_to_document(row: Any) -> GuidanceDocument | None:
    cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
    if len(cells) < 2:
        return None
    link = row.find("a", href=True)
    if link is None:
        return None
    title = _clean_text(link.get_text(" ", strip=True)) or cells[0]
    if not title:
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
    if not title:
        return None

    product_area = _first_value(item, "productArea", "drugType", "scope", "适用范围", "fclass")
    if product_area and not any(area in product_area for area in CDE_ALLOWED_PRODUCT_AREAS):
        return None

    document_value = _first_value(item, "document_url", "fileUrl", "attachmentUrl")
    return _build_document(
        title=title,
        source_page_url=_item_source_url(item),
        document_url=_optional_url(document_value),
        document_format=_first_value(item, "document_format", "fileFormat") or _document_format(document_value),
        published_date=parse_date(_first_value(item, "published_date", "publishDate", "date", "发布日期", "issueDate")),
        updated_date=parse_date(_first_value(item, "updated_date", "updateDate")),
        product_area=product_area or None,
        summary=_first_value(item, "summary", "content", "description") or "Not available.",
        status_raw=_first_value(item, "status", "nowstate", "versionState"),
        reference_number=_first_value(item, "zdyzIdCODE", "idCODE", "id") or None,
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
    document_format: str | None = None,
    status_raw: str | None = None,
    reference_number: str | None = None,
) -> GuidanceDocument:
    document_url = document_url or None
    status, sub_status = normalize_status(title, status_raw, "CDE")
    return GuidanceDocument(
        title=title,
        agency="CDE",
        jurisdiction="China",
        source_page_url=source_page_url or CDE_GUIDANCE_URL,
        document_url=document_url,
        document_format=document_format or _document_format(document_url),
        published_date=published_date if hasattr(published_date, "year") else parse_date(published_date),
        updated_date=updated_date if hasattr(updated_date, "year") else parse_date(updated_date),
        status_raw=status_raw,
        status_normalized=status,
        sub_status=sub_status,
        topic_raw=product_area,
        topic_normalized=normalize_topic(title, product_area, summary),
        product_area=product_area,
        summary=summary or "Not available.",
        language="ZH",
        reference_number=reference_number,
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


def _item_source_url(item: dict[str, Any]) -> str:
    explicit_url = _first_value(item, "url", "href", "link", "source_page_url")
    if explicit_url:
        return urljoin(CDE_BASE_URL, explicit_url)
    code = _first_value(item, "zdyzIdCODE", "idCODE", "id")
    if code:
        return f"{CDE_BASE_URL}/zdyz/domesticinfopage?zdyzIdCODE={code}"
    return CDE_GUIDANCE_URL


def _optional_url(value: str) -> str | None:
    if not value:
        return None
    return urljoin(CDE_BASE_URL, value)


def _enrich_items_with_detail_links(context: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in items:
        copied = dict(item)
        detail_url = _item_source_url(copied)
        try:
            response = context.request.get(detail_url, timeout=30_000)
            if response.ok:
                document_url, document_format = extract_cde_attachment_from_html(response.text())
                if document_url:
                    copied["document_url"] = document_url
                if document_format:
                    copied["document_format"] = document_format
        except Exception as exc:  # pragma: no cover - best-effort live enrichment
            logger.warning("CDE detail attachment fetch failed for %s: %s", detail_url, exc)
        enriched.append(copied)
    return enriched


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = _first_value(item, "zdyzIdCODE", "idCODE", "id") or _first_value(item, "title", "name")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


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


def _document_format(url: str | None, filename: str | None = None) -> str | None:
    text = f"{url or ''} {filename or ''}"
    if not text.strip():
        return None
    lowered = text.strip().lower()
    if lowered.endswith(".pdf"):
        return "PDF"
    if lowered.endswith((".doc", ".docx")):
        return "DOCX"
    return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())
