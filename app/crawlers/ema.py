from __future__ import annotations

import logging
from typing import Any, Callable

import httpx

from app.crawlers.base import BaseCrawler
from app.normalizers.dates import parse_date
from app.normalizers.status import normalize_status
from app.normalizers.topics import normalize_topic
from app.storage.models import GuidanceDocument


logger = logging.getLogger(__name__)

EMA_GENERAL_JSON_URL = "https://www.ema.europa.eu/en/documents/report/general-json-report_en.json?download=1"

FetchJson = Callable[[], dict[str, Any]]


class EMACrawler(BaseCrawler):
    agency = "EMA"
    jurisdiction = "EU"

    def __init__(self, fetch_json: FetchJson | None = None) -> None:
        self.fetch_json = fetch_json or fetch_ema_guidance_json

    def crawl(self) -> list[GuidanceDocument]:
        try:
            return parse_ema_guidance_payload(self.fetch_json())
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("EMA crawler failed: %s", exc)
            return []


def fetch_ema_guidance_json() -> dict[str, Any]:
    response = httpx.get(
        EMA_GENERAL_JSON_URL,
        headers={
            "Accept": "application/json",
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


def parse_ema_guidance_payload(payload: dict[str, Any]) -> list[GuidanceDocument]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("EMA JSON payload does not contain a data list")
    return [document for row in data if isinstance(row, dict) and (document := _row_to_document(row)) is not None]


def _row_to_document(row: dict[str, Any]) -> GuidanceDocument | None:
    title = _clean_text(row.get("title"))
    url = _clean_text(row.get("general_url"))
    if not title or not url or not _is_guidance_row(title, url):
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


def _is_guidance_row(title: str, url: str) -> bool:
    lowered_title = title.lower()
    lowered_url = url.lower()
    return (
        "scientific guideline" in lowered_title
        or "guidance" in lowered_title
        or "guideline" in lowered_title
        or lowered_url.endswith("-scientific-guideline")
        or "/scientific-guidelines/" in lowered_url
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


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())
