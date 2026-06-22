from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any

import httpx
from app.crawlers.base import BaseCrawler
from app.normalizers.dates import parse_date
from app.normalizers.status import normalize_status
from app.normalizers.topics import normalize_topic
from app.storage.models import GuidanceDocument
from guidance_collector.fda import FDAFetchError, collect_fda_static_guidance, extract_guidance_summary_from_html
from guidance_collector.schema import GuidanceRecord


logger = logging.getLogger(__name__)


class FDACrawler(BaseCrawler):
    agency = "FDA"
    jurisdiction = "US"

    def __init__(self, max_records: int | None = 50) -> None:
        self.max_records = max_records

    def crawl(self) -> list[GuidanceDocument]:
        try:
            records = collect_fda_static_guidance(
                fetch_json=_fetch_static_json_httpx,
                max_records=self.max_records,
            )
            records = _enrich_records_with_detail_summaries(records)
        except (FDAFetchError, httpx.HTTPError, ValueError) as exc:
            logger.warning("FDA crawler failed: %s", exc)
            return []

        documents: list[GuidanceDocument] = []
        for record in records:
            published_date = parse_date(record.issue_date)
            comment_end_date = parse_date(record.comment_closing_date_on_draft)
            status, sub_status = normalize_status(
                record.guidance_name,
                record.guidance_status,
                "FDA",
                comment_end_date=comment_end_date,
            )
            topic = normalize_topic(record.guidance_name, record.topic, record.summary)
            documents.append(
                GuidanceDocument(
                    title=record.guidance_name,
                    agency="FDA",
                    jurisdiction="US",
                    source_page_url=record.guidance_page_link or None,
                    document_url=record.guidance_pdf_link or None,
                    document_format="PDF" if record.guidance_pdf_link else None,
                    published_date=published_date,
                    comment_end_date=comment_end_date,
                    status_raw=record.guidance_status,
                    status_normalized=status,
                    sub_status=sub_status,
                    topic_raw=record.topic,
                    topic_normalized=topic,
                    summary=record.summary,
                    language="EN",
                    reference_number=record.docket_number or None,
                    needs_manual_review=False,
                )
            )
        return documents


def _fetch_static_json_httpx(url: str) -> list[Any]:
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=60,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 reg-guidance-tracker/0.1",
            "Referer": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
        },
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"FDA static JSON returned {type(payload).__name__}, expected list")
    return payload


def _enrich_records_with_detail_summaries(records: list[GuidanceRecord]) -> list[GuidanceRecord]:
    with httpx.Client(
        follow_redirects=True,
        timeout=30,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 reg-guidance-tracker/0.1",
            "Referer": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
        },
    ) as client:
        with ThreadPoolExecutor(max_workers=6) as executor:
            return list(executor.map(lambda record: _enrich_one_record(client, record), records))


def _enrich_one_record(client: httpx.Client, record: GuidanceRecord) -> GuidanceRecord:
    if not record.guidance_page_link:
        return record
    for attempt in range(3):
        try:
            response = client.get(record.guidance_page_link)
            response.raise_for_status()
            summary = extract_guidance_summary_from_html(response.text)
            return replace(record, summary=summary or record.summary)
        except httpx.HTTPError as exc:
            if attempt == 2:
                logger.warning("FDA detail summary fetch failed for %s: %s", record.guidance_page_link, exc)
                return record
            time.sleep(0.5 * (attempt + 1))
    return record
