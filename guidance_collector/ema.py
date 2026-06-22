from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib import request
from urllib.error import HTTPError, URLError

from .fda import FDAFetchError, normalize_whitespace
from .schema import GuidanceRecord, write_csv, write_json


EMA_GENERAL_JSON_URL = "https://www.ema.europa.eu/en/documents/report/general-json-report_en.json"
EMA_ORGANIZATION = "European Medicines Agency"

FetchJson = Callable[[str], dict[str, Any]]


class EMAFetchError(RuntimeError):
    """Raised when the official EMA JSON feed cannot be fetched."""


def parse_ema_general_payload(payload: dict[str, Any]) -> list[GuidanceRecord]:
    return [parse_ema_general_row(row) for row in payload.get("data", []) if is_ema_guidance_row(row)]


def parse_ema_general_row(row: dict[str, Any]) -> GuidanceRecord:
    raw_title = normalize_whitespace(row.get("title"))
    name, status = split_ema_title_status(raw_title)
    categories = normalize_whitespace(row.get("categories")).replace(";", "; ")
    return GuidanceRecord(
        health_authority="EMA",
        guidance_name=name,
        summary=normalize_whitespace(row.get("summary")),
        issue_date=normalize_ema_date(row.get("first_published_date")),
        fda_organization=EMA_ORGANIZATION,
        topic=categories,
        guidance_status=status,
        open_for_comment=open_for_comment_from_status(status),
        comment_closing_date_on_draft=consultation_closing_date(row.get("consultation_date", "")),
        guidance_pdf_link="",
        guidance_page_link=normalize_whitespace(row.get("general_url")),
        docket_number=normalize_whitespace(row.get("reference_number")),
    )


def collect_ema_guidance(
    fetch_json: FetchJson | None = None,
    max_records: int | None = None,
) -> list[GuidanceRecord]:
    fetch = fetch_json or fetch_json_url
    records = parse_ema_general_payload(fetch(EMA_GENERAL_JSON_URL))
    if max_records is not None:
        return records[:max_records]
    return records


def fetch_json_url(url: str) -> dict[str, Any]:
    req = request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 guidance-collector/0.1",
        },
    )
    try:
        with request.urlopen(req, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise EMAFetchError(f"EMA JSON request failed with HTTP {exc.code}: {url}") from exc
    except json.JSONDecodeError as exc:
        raise EMAFetchError(f"EMA JSON feed returned a non-JSON response: {url}") from exc
    except URLError as exc:
        raise EMAFetchError(f"EMA JSON request failed: {url} ({exc.reason})") from exc
    except TimeoutError as exc:
        raise EMAFetchError(f"EMA JSON request timed out: {url}") from exc


def is_ema_guidance_row(row: dict[str, Any]) -> bool:
    title = normalize_whitespace(row.get("title")).lower()
    url = normalize_whitespace(row.get("general_url")).lower()
    return "scientific guideline" in title or url.endswith("-scientific-guideline")


def split_ema_title_status(title: str) -> tuple[str, str]:
    marker = " - Scientific guideline"
    if title.endswith(marker):
        return title[: -len(marker)].strip(), "Scientific guideline"
    return title, "Guidance"


def open_for_comment_from_status(status: str) -> str:
    lowered = status.lower()
    if "draft" in lowered or "consultation" in lowered:
        return "Yes"
    return ""


def consultation_closing_date(value: Any) -> str:
    text = normalize_whitespace(value)
    if " to " not in text:
        return normalize_ema_date(text)
    return normalize_ema_date(text.rsplit(" to ", 1)[-1])


def normalize_ema_date(value: Any) -> str:
    text = normalize_whitespace(value)
    if not text:
        return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect EMA scientific guideline pages.")
    parser.add_argument("--output", "-o", default="exports/ema_guidance.csv", help="Output file path.")
    parser.add_argument("--format", choices=("csv", "json"), default="csv", help="Export format.")
    parser.add_argument("--max-records", type=int, default=None, help="Optional cap for test runs.")
    args = parser.parse_args(argv)

    try:
        records = collect_ema_guidance(max_records=args.max_records)
    except (EMAFetchError, FDAFetchError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        if args.format == "csv":
            write_csv(records, handle)
        else:
            write_json(records, handle)
    print(f"Wrote {len(records)} EMA guidance records to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
