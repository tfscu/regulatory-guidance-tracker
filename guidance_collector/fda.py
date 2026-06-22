from __future__ import annotations

import argparse
import http.client
import json
import re
import sys
from dataclasses import replace
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib import parse, request
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup

from .schema import GuidanceRecord, write_csv, write_json


FDA_BASE_URL = "https://www.fda.gov"
FDA_DATATABLE_URL = f"{FDA_BASE_URL}/datatables-json/search-for-guidance.json"
FDA_STATIC_DATATABLE_URL = f"{FDA_BASE_URL}/files/api/datatables/static/search-for-guidance.json"


FetchJson = Callable[[str, dict[str, int]], dict[str, Any]]
FetchText = Callable[[str], str]


class FDAFetchError(RuntimeError):
    """Raised when the official FDA guidance endpoint cannot be fetched."""


class _CellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self.links.append(parse.urljoin(FDA_BASE_URL, href))

    def handle_data(self, data: str) -> None:
        if data:
            self.text_parts.append(data)

    @property
    def text(self) -> str:
        return normalize_whitespace(" ".join(self.text_parts))


class _ParagraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self._in_paragraph = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "p":
            self._in_paragraph = True
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._in_paragraph:
            text = normalize_whitespace(" ".join(self._parts))
            if text:
                self.paragraphs.append(text)
            self._in_paragraph = False
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_paragraph and data:
            self._parts.append(data)


def normalize_whitespace(value: Any) -> str:
    text = unescape("" if value is None else str(value))
    return re.sub(r"\s+", " ", text).strip()


def parse_html_cell(value: Any) -> tuple[str, list[str]]:
    parser = _CellParser()
    parser.feed("" if value is None else str(value))
    return parser.text or normalize_whitespace(value), parser.links


def normalize_date(value: Any) -> str:
    text = normalize_whitespace(value)
    if not text:
        return ""
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return text


def normalize_yes_no(value: Any) -> str:
    text = normalize_whitespace(value)
    lowered = text.lower()
    if lowered in {"yes", "y", "true", "1"}:
        return "Yes"
    if lowered in {"no", "n", "false", "0"}:
        return "No"
    return text


def extract_guidance_summary_from_html(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    containers = [
        soup.select_one("div[role='main']"),
        soup.select_one("article.main-content"),
        soup.select_one("article"),
        soup.select_one("main"),
        soup,
    ]
    for container in containers:
        if not container:
            continue
        for paragraph_node in container.find_all("p"):
            paragraph = normalize_whitespace(paragraph_node.get_text(" ", strip=True))
            if _is_guidance_summary_candidate(paragraph):
                return paragraph

    parser = _ParagraphParser()
    parser.feed(html_text)
    for paragraph in parser.paragraphs:
        if _is_guidance_summary_candidate(paragraph):
            return paragraph
    return ""


def enrich_with_detail_summaries(
    records: Iterable[GuidanceRecord],
    fetch_text: FetchText | None = None,
) -> list[GuidanceRecord]:
    fetch = fetch_text or fetch_text_url
    enriched: list[GuidanceRecord] = []
    for record in records:
        if not record.guidance_page_link:
            enriched.append(record)
            continue
        summary = extract_guidance_summary_from_html(fetch(record.guidance_page_link))
        enriched.append(replace(record, summary=summary or record.summary))
    return enriched


def parse_fda_datatables_payload(payload: dict[str, Any]) -> list[GuidanceRecord]:
    return [parse_fda_row(row) for row in payload.get("data", [])]


def parse_fda_static_payload(payload: list[Any]) -> list[GuidanceRecord]:
    return [parse_fda_row(row) for row in payload]


def parse_fda_row(row: Any) -> GuidanceRecord:
    cells = _row_to_cells(row)
    summary_text, summary_links = parse_html_cell(cells["summary"])
    document_text, document_links = parse_html_cell(cells["document"])
    docket_text, _docket_links = parse_html_cell(cells["docket_number"])

    guidance_name = summary_text
    pdf_link = _first_pdf_or_download_link(document_links)
    page_link = summary_links[0] if summary_links else ""

    return GuidanceRecord(
        health_authority="FDA",
        guidance_name=guidance_name,
        summary=summary_text,
        issue_date=normalize_date(cells["issue_date"]),
        fda_organization=normalize_whitespace(cells["organization"]),
        topic=normalize_whitespace(cells["topic"]),
        guidance_status=normalize_whitespace(cells["guidance_status"]),
        open_for_comment=normalize_yes_no(cells["open_for_comment"]),
        comment_closing_date_on_draft=normalize_date(cells["comment_closing_date"]),
        guidance_pdf_link=pdf_link or document_text,
        guidance_page_link=page_link,
        docket_number=docket_text,
    )


def collect_fda_guidance(
    fetch_json: FetchJson | None = None,
    fetch_text: FetchText | None = None,
    page_size: int = 500,
    max_records: int | None = None,
    include_detail_summaries: bool = True,
) -> list[GuidanceRecord]:
    fetch = fetch_json or fetch_json_url
    records: list[GuidanceRecord] = []
    start = 0
    draw = 1
    total: int | None = None

    while total is None or start < total:
        length = page_size if max_records is None else min(page_size, max_records - len(records))
        if length <= 0:
            break
        params = {"draw": draw, "start": start, "length": length}
        payload = fetch(FDA_DATATABLE_URL, params)
        total = int(payload.get("recordsFiltered") or payload.get("recordsTotal") or 0)
        page_records = parse_fda_datatables_payload(payload)
        if not page_records:
            break
        records.extend(page_records)
        if max_records is not None and len(records) >= max_records:
            records = records[:max_records]
            break
        start += len(page_records)
        draw += 1

    if include_detail_summaries:
        records = enrich_with_detail_summaries(records, fetch_text=fetch_text)
    return records


def collect_fda_static_guidance(
    fetch_json: Callable[[str], list[Any]] | None = None,
    max_records: int | None = None,
) -> list[GuidanceRecord]:
    fetch = fetch_json or fetch_static_json_url
    records = sorted(
        parse_fda_static_payload(fetch(FDA_STATIC_DATATABLE_URL)),
        key=lambda record: record.issue_date or "",
        reverse=True,
    )
    if max_records is not None:
        return records[:max_records]
    return records


def fetch_json_url(url: str, params: dict[str, int]) -> dict[str, Any]:
    query_url = f"{url}?{parse.urlencode(params)}"
    req = request.Request(
        query_url,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 guidance-collector/0.1",
            "Referer": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
        },
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise FDAFetchError(f"FDA endpoint request failed with HTTP {exc.code}: {query_url}") from exc
    except json.JSONDecodeError as exc:
        raise FDAFetchError(f"FDA endpoint returned a non-JSON response: {query_url}") from exc
    except URLError as exc:
        raise FDAFetchError(f"FDA endpoint request failed: {query_url} ({exc.reason})") from exc
    except http.client.RemoteDisconnected as exc:
        raise FDAFetchError(f"FDA endpoint closed the connection without a response: {query_url}") from exc
    except TimeoutError as exc:
        raise FDAFetchError(f"FDA endpoint request timed out: {query_url}") from exc


def fetch_static_json_url(url: str) -> list[Any]:
    req = request.Request(
        url,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 guidance-collector/0.1",
            "Referer": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
        },
    )
    try:
        with request.urlopen(req, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise FDAFetchError(f"FDA static JSON request failed with HTTP {exc.code}: {url}") from exc
    except json.JSONDecodeError as exc:
        raise FDAFetchError(f"FDA static JSON returned a non-JSON response: {url}") from exc
    except URLError as exc:
        raise FDAFetchError(f"FDA static JSON request failed: {url} ({exc.reason})") from exc
    except http.client.RemoteDisconnected as exc:
        raise FDAFetchError(f"FDA static JSON closed the connection without a response: {url}") from exc
    except TimeoutError as exc:
        raise FDAFetchError(f"FDA static JSON request timed out: {url}") from exc
    if not isinstance(payload, list):
        raise FDAFetchError(f"FDA static JSON returned {type(payload).__name__}, expected list: {url}")
    return payload


def fetch_text_url(url: str) -> str:
    req = request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 guidance-collector/0.1",
            "Referer": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
        },
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise FDAFetchError(f"FDA detail page request failed with HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise FDAFetchError(f"FDA detail page request failed: {url} ({exc.reason})") from exc
    except http.client.RemoteDisconnected as exc:
        raise FDAFetchError(f"FDA detail page closed the connection without a response: {url}") from exc
    except TimeoutError as exc:
        raise FDAFetchError(f"FDA detail page request timed out: {url}") from exc


def _row_to_cells(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return {
            "summary": _first_present(row, "field_summary", "summary", "title", "0"),
            "document": _first_present(row, "field_document", "field_associated_media_2", "document", "1"),
            "issue_date": _first_present(row, "field_issue_date", "field_issue_datetime", "issue_date", "2"),
            "organization": _first_present(
                row,
                "field_organization",
                "field_issuing_office_taxonomy",
                "organization",
                "fda_organization",
                "3",
            ),
            "topic": _first_present(row, "field_topic", "topics-product", "field_topics", "topic", "4"),
            "guidance_status": _first_present(
                row,
                "field_guidance_status",
                "field_final_guidance_1",
                "guidance_status",
                "status",
                "5",
            ),
            "open_for_comment": _first_present(row, "field_open_for_comment", "open-comment", "open_for_comment", "6"),
            "comment_closing_date": _first_present(
                row,
                "field_comment_closing_date",
                "field_comment_closing_date_on_draft",
                "field_comment_close_date",
                "comment_closing_date",
                "7",
            ),
            "docket_number": _first_present(row, "field_docket_number", "docket_number", "8"),
        }
    if isinstance(row, (list, tuple)):
        padded = list(row) + [""] * 9
        return {
            "summary": padded[0],
            "document": padded[1],
            "issue_date": padded[2],
            "organization": padded[3],
            "topic": padded[4],
            "guidance_status": padded[5],
            "open_for_comment": padded[6],
            "comment_closing_date": padded[7],
            "docket_number": padded[8],
        }
    raise TypeError(f"Unsupported FDA row type: {type(row).__name__}")


def _first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return ""


def _first_pdf_or_download_link(links: Iterable[str]) -> str:
    for link in links:
        lowered = link.lower()
        if lowered.endswith(".pdf") or "/media/" in lowered or "download" in lowered:
            return link
    return next(iter(links), "")


def _is_guidance_summary_candidate(paragraph: str) -> bool:
    lowered = paragraph.lower()
    if len(paragraph) < 80:
        return False
    boilerplate_markers = (
        ".gov means it’s official",
        ".gov means it's official",
        "federal government websites often end in .gov",
        "before sharing sensitive information",
        "guidance document",
        "not for implementation",
        "contains non-binding recommendations",
        "search for fda guidance documents",
        "you can submit online",
        "although you can comment on any guidance at any time",
        "if unable to submit comments online",
        "dockets management",
        "all written comments",
        "omb control number",
        "was this page helpful",
    )
    return not any(marker in lowered for marker in boilerplate_markers)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect FDA guidance documents.")
    parser.add_argument("--output", "-o", default="exports/fda_guidance.csv", help="Output file path.")
    parser.add_argument("--format", choices=("csv", "json"), default="csv", help="Export format.")
    parser.add_argument("--page-size", type=int, default=500, help="FDA pagination size.")
    parser.add_argument("--max-records", type=int, default=None, help="Optional cap for test runs.")
    parser.add_argument(
        "--skip-detail-summaries",
        action="store_true",
        help="Keep Summary as the table title instead of fetching each guidance detail page.",
    )
    args = parser.parse_args(argv)

    try:
        records = collect_fda_guidance(
            page_size=args.page_size,
            max_records=args.max_records,
            include_detail_summaries=not args.skip_detail_summaries,
        )
    except FDAFetchError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        if args.format == "csv":
            write_csv(records, handle)
        else:
            write_json(records, handle)
    print(f"Wrote {len(records)} FDA guidance records to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
