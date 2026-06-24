from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import re
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

EMA_GENERAL_JSON_URL = "https://www.ema.europa.eu/en/documents/report/general-json-report_en.json"
EMA_GENERAL_JSON_FALLBACK_URL = f"{EMA_GENERAL_JSON_URL}?download=1"
EMA_SEARCH_URL = "https://www.ema.europa.eu/en/search?f%5B0%5D=ema_search_custom_entity_bundle%3A004_ema_guidance_and_info"
EMA_BASE_URL = "https://www.ema.europa.eu"

FetchJson = Callable[[], dict[str, Any]]
FetchText = Callable[[str], str]
FetchCount = Callable[[], int | None]


class EMACompletenessError(ValueError):
    pass


class EMACrawler(BaseCrawler):
    agency = "EMA"
    jurisdiction = "EU"

    def __init__(
        self,
        fetch_json: FetchJson | None = None,
        fetch_detail_html: FetchText | None = None,
        fetch_search_count: FetchCount | None = None,
        pdf_workers: int = 24,
    ) -> None:
        self.fetch_json = fetch_json or fetch_ema_guidance_json
        self.fetch_detail_html = fetch_detail_html if fetch_detail_html is not None else (
            fetch_ema_detail_html if fetch_json is None else None
        )
        self.fetch_search_count = fetch_search_count if fetch_search_count is not None else (
            fetch_ema_guidance_search_count if fetch_json is None else None
        )
        self.pdf_workers = pdf_workers

    def crawl(self) -> list[GuidanceDocument]:
        try:
            payload = self.fetch_json()
            documents = parse_ema_guidance_payload(payload)
            if self.fetch_search_count is not None:
                validate_ema_guidance_completeness(payload, documents, self.fetch_search_count())
            if self.fetch_detail_html is None:
                return documents
            return enrich_ema_documents_with_pdf_links(documents, self.fetch_detail_html, workers=self.pdf_workers)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("EMA crawler failed: %s", exc)
            return []


def fetch_ema_guidance_json() -> dict[str, Any]:
    errors: list[Exception] = []
    for url in (EMA_GENERAL_JSON_URL, EMA_GENERAL_JSON_FALLBACK_URL):
        try:
            return _fetch_ema_guidance_json_url(url)
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(exc)
            logger.warning("EMA JSON fetch failed for %s: %s", url, exc)
    raise ValueError(f"EMA JSON fetch failed for all configured URLs: {errors[-1] if errors else 'unknown error'}")


def fetch_ema_guidance_search_count() -> int | None:
    response = httpx.get(
        EMA_SEARCH_URL,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 reg-guidance-tracker/0.1",
        },
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()
    return parse_ema_guidance_search_count(response.text)


def _fetch_ema_guidance_json_url(url: str) -> dict[str, Any]:
    response = httpx.get(
        url,
        headers={
            "Accept": "application/json,*/*",
            "Referer": "https://www.ema.europa.eu/en/about-us/about-website/download-website-data-json-data-format",
            "User-Agent": "Mozilla/5.0 reg-guidance-tracker/0.1",
        },
        timeout=90,
        follow_redirects=True,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"EMA JSON returned {type(payload).__name__}, expected object")
    return payload


def fetch_ema_detail_html(url: str) -> str:
    response = httpx.get(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Referer": EMA_BASE_URL,
            "User-Agent": "Mozilla/5.0 reg-guidance-tracker/0.1",
        },
        timeout=15,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def parse_ema_guidance_payload(payload: dict[str, Any]) -> list[GuidanceDocument]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("EMA JSON payload does not contain a data list")
    return [document for row in data if isinstance(row, dict) and (document := _row_to_document(row)) is not None]


def parse_ema_guidance_search_count(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    active_facet = soup.select_one(
        'a.is-active[data-drupal-facet-item-value="004_ema_guidance_and_info"][data-drupal-facet-item-count]'
    )
    if active_facet:
        return _parse_int(active_facet.get("data-drupal-facet-item-count"))

    heading = soup.find(string=re.compile(r"Search results", re.IGNORECASE))
    if heading:
        heading_container = heading.find_parent(["h1", "h2", "h3"]) if hasattr(heading, "find_parent") else None
        heading_text = (
            heading_container.get_text(" ", strip=True)
            if heading_container
            else heading.parent.get_text(" ", strip=True) if heading.parent else str(heading)
        )
        match = re.search(r"Search results\s*\(?\s*([\d,]+)\s*\)?", heading_text, re.IGNORECASE)
        if match:
            return _parse_int(match.group(1))
    return None


def validate_ema_guidance_completeness(
    payload: dict[str, Any], documents: list[GuidanceDocument], search_count: int | None
) -> None:
    if search_count is None:
        logger.warning("EMA search result count was not available; imported JSON rows cannot be cross-checked.")
        return

    json_count = _payload_total_records(payload) or len(documents)
    if json_count != search_count or len(documents) != search_count:
        raise EMACompletenessError(
            "EMA JSON import is incomplete against the EMA search page: "
            f"search page reports {search_count} Guidance and information records, "
            f"JSON reports {json_count}, parsed import has {len(documents)}. "
            "Supplemental search-page crawling is required before refreshing EMA records."
        )


def enrich_ema_documents_with_pdf_links(
    documents: list[GuidanceDocument], fetch_detail_html: FetchText, workers: int = 24
) -> list[GuidanceDocument]:
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        return list(executor.map(lambda document: _enrich_ema_document_with_pdf_link(document, fetch_detail_html), documents))


def _enrich_ema_document_with_pdf_link(document: GuidanceDocument, fetch_detail_html: FetchText) -> GuidanceDocument:
    if not document.source_page_url:
        return document
    try:
        pdf_url = extract_ema_pdf_url_from_html(fetch_detail_html(document.source_page_url))
        if pdf_url:
            document.document_url = pdf_url
            document.document_format = "PDF"
    except httpx.HTTPError as exc:
        logger.warning("EMA PDF link fetch failed for %s: %s", document.source_page_url, exc)
    return document


def extract_ema_pdf_url_from_html(html: str, base_url: str = EMA_BASE_URL) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        href = str(link.get("href") or "")
        if ".pdf" in href.lower() and "/documents/" in href.lower():
            return urljoin(base_url, href)
    return None


def _row_to_document(row: dict[str, Any]) -> GuidanceDocument | None:
    title = _clean_text(row.get("title"))
    url = _clean_text(row.get("general_url"))
    if not title or not url:
        return None

    name, status_raw = _split_title_status(title)
    summary = _clean_text(row.get("summary")) or "Not available."
    status, sub_status = normalize_status(name, status_raw, "EMA")
    topic_raw = _clean_text(row.get("categories"))

    return GuidanceDocument(
        title=name,
        agency="EMA",
        jurisdiction="EU",
        source_page_url=url,
        document_url=None,
        document_format=None,
        published_date=parse_date(row.get("first_published_date")),
        updated_date=parse_date(row.get("last_updated_date")),
        comment_end_date=parse_date(_consultation_closing_date(row.get("consultation_date"))),
        status_raw=status_raw,
        status_normalized=status,
        sub_status=sub_status,
        topic_raw=topic_raw,
        topic_normalized=normalize_topic(name, topic_raw, summary),
        summary=summary,
        language="EN",
        reference_number=_clean_text(row.get("reference_number")) or None,
        needs_manual_review=False,
    )

def _split_title_status(title: str) -> tuple[str, str]:
    for marker, status in (
        (" - Scientific guideline", "Scientific guideline"),
        (" - Regulatory and procedural guideline", "Regulatory and procedural guideline"),
    ):
        if title.endswith(marker):
            return title[: -len(marker)].strip(), status
    return title, "Guidance"


def _consultation_closing_date(value: Any) -> str:
    text = _clean_text(value)
    if " to " not in text:
        return text
    return text.rsplit(" to ", 1)[-1]


def _payload_total_records(payload: dict[str, Any]) -> int | None:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return None
    return _parse_int(meta.get("total_records"))


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).replace(",", "").strip()
    if not text.isdigit():
        return None
    return int(text)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())
