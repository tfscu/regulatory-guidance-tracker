from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from app.crawlers.base import BaseCrawler
from app.normalizers.dates import parse_date
from app.normalizers.status import normalize_status
from app.normalizers.topics import normalize_topic
from app.storage.models import GuidanceDocument


logger = logging.getLogger(__name__)

PMDA_BASE_URL = "https://www.pmda.go.jp"
PMDA_CLINICAL_TRIALS_URL = f"{PMDA_BASE_URL}/english/review-services/regulatory-info/0016.html"
PMDA_VACCINES_URL = f"{PMDA_BASE_URL}/english/review-services/regulatory-info/0018.html"
VACCINE_SECTIONS = {
    "Clinical Studies",
    "Prototype Vaccines",
    "Vaccines Against the Novel Coronavirus SARS-CoV-2",
}
DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},\s+\d{4}\b"
)
FILE_SIZE_RE = re.compile(r"\s*[\[［]\s*[\d.,]+\s*(?:KB|MB)\s*[\]］]\s*$", re.IGNORECASE)

FetchPages = Callable[[], dict[str, str]]


@dataclass(frozen=True)
class PMDASource:
    url: str
    product_area: str
    allowed_sections: frozenset[str] | None = None
    required_parent_section: str | None = None


PMDA_SOURCES = (
    PMDASource(PMDA_CLINICAL_TRIALS_URL, "Drug clinical trials"),
    PMDASource(
        PMDA_VACCINES_URL,
        "Vaccines",
        frozenset(VACCINE_SECTIONS),
        "Vaccines for Infectious Disease",
    ),
)


class PMDACrawler(BaseCrawler):
    agency = "PMDA"
    jurisdiction = "Japan"

    def __init__(self, fetch_pages: FetchPages | None = None) -> None:
        self.fetch_pages = fetch_pages or fetch_pmda_pages

    def crawl(self) -> list[GuidanceDocument]:
        try:
            return parse_pmda_pages(self.fetch_pages())
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("PMDA crawler failed: %s", exc)
            return []


def fetch_pmda_pages() -> dict[str, str]:
    pages: dict[str, str] = {}
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "User-Agent": "Mozilla/5.0 reg-guidance-tracker/0.1",
    }
    with httpx.Client(headers=headers, timeout=60, follow_redirects=True) as client:
        for source in PMDA_SOURCES:
            response = client.get(source.url)
            response.raise_for_status()
            pages[source.url] = response.text
    return pages


def parse_pmda_pages(pages: dict[str, str]) -> list[GuidanceDocument]:
    documents: list[GuidanceDocument] = []
    for source in PMDA_SOURCES:
        html = pages.get(source.url)
        if not html:
            raise ValueError(f"PMDA response missing required source page: {source.url}")
        parsed = parse_pmda_guidance_html(html, source)
        if not parsed:
            raise ValueError(f"PMDA source page returned no in-scope documents: {source.url}")
        documents.extend(parsed)
    return _dedupe_documents(documents)


def parse_pmda_guidance_html(html: str, source: PMDASource) -> list[GuidanceDocument]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main")
    if main is None:
        raise ValueError("PMDA page does not contain a main content area")

    current_h2 = ""
    current_h3 = ""
    current_h4 = ""
    documents: list[GuidanceDocument] = []

    for element in main.find_all(["h2", "h3", "h4", "a"]):
        text = _clean_text(element.get_text(" ", strip=True))
        if element.name == "h2":
            current_h2 = text
            current_h3 = ""
            current_h4 = ""
            continue
        if element.name == "h3":
            current_h3 = text
            current_h4 = ""
            continue
        if element.name == "h4":
            current_h4 = text
            continue
        if current_h2 != "Regulations and Notifications":
            continue
        if source.required_parent_section and current_h3 != source.required_parent_section:
            continue
        if source.allowed_sections is not None and current_h4 not in source.allowed_sections:
            continue

        document = _link_to_document(element, source, current_h4)
        if document is not None:
            documents.append(document)

    return _dedupe_documents(documents)


def _link_to_document(link: Tag, source: PMDASource, section: str) -> GuidanceDocument | None:
    href = _clean_text(link.get("href"))
    if not href or "/files/" not in href:
        return None

    title = _clean_title(link.get_text(" ", strip=True))
    if not title:
        return None

    document_url = urljoin(PMDA_BASE_URL, href)
    metadata = _document_metadata(link)
    date_match = DATE_RE.search(metadata)
    published_date = parse_date(date_match.group(0)) if date_match else None
    status_raw = metadata[date_match.end() :].strip(" -") if date_match else metadata or None
    status, sub_status = normalize_status(title, status_raw, "PMDA")
    if status == "unknown":
        status = "final"
    if "early consideration" in title.lower():
        sub_status = "early_consideration"

    topic_raw = f"{source.product_area} / {section}" if section else source.product_area
    return GuidanceDocument(
        title=title,
        agency="PMDA",
        jurisdiction="Japan",
        source_page_url=source.url,
        document_url=document_url,
        document_format="PDF" if urlparse(document_url).path.lower().endswith(".pdf") else None,
        published_date=published_date,
        status_raw=status_raw,
        status_normalized=status,
        sub_status=sub_status,
        topic_raw=topic_raw,
        topic_normalized=normalize_topic(title, topic_raw, None),
        product_area=source.product_area,
        summary="Not available.",
        language="EN",
        reference_number=urlparse(document_url).path.rsplit("/", 1)[-1].rsplit(".", 1)[0],
        needs_manual_review=published_date is None,
    )


def _document_metadata(link: Tag) -> str:
    item = link.find_parent("li")
    if item is not None:
        item_text = _clean_text(item.get_text(" ", strip=True))
        link_text = _clean_text(link.get_text(" ", strip=True))
        remaining = item_text[len(link_text) :].strip() if item_text.startswith(link_text) else item_text
        if DATE_RE.search(remaining):
            return remaining

    listing = link.find_parent("ul")
    sibling = listing.find_next_sibling() if listing is not None else None
    if isinstance(sibling, Tag) and sibling.name == "p":
        return _clean_text(sibling.get_text(" ", strip=True))
    return ""


def _dedupe_documents(documents: list[GuidanceDocument]) -> list[GuidanceDocument]:
    seen: set[str] = set()
    deduped: list[GuidanceDocument] = []
    for document in documents:
        key = (document.document_url or f"{document.source_page_url}|{document.title}").lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(document)
    return deduped


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _clean_title(value: object) -> str:
    title = FILE_SIZE_RE.sub("", _clean_text(value)).strip(" -–—")
    if title.lower().startswith("(attachment)"):
        title = title[len("(Attachment)") :].strip()
    return title
