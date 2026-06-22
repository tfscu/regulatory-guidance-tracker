from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from typing import Iterable, TextIO


EXPORT_COLUMNS = [
    "Health Authority",
    "Guidance Name",
    "Summary",
    "Issue Date",
    "FDA Organization",
    "Topic",
    "Guidance Status",
    "Open for Comment",
    "Comment Closing Date on Draft",
    "Guidance PDF Link",
    "Guidance Page Link",
    "Docket Number",
]


@dataclass(frozen=True)
class GuidanceRecord:
    health_authority: str
    guidance_name: str
    summary: str
    issue_date: str
    fda_organization: str
    topic: str
    guidance_status: str
    open_for_comment: str
    comment_closing_date_on_draft: str
    guidance_pdf_link: str
    guidance_page_link: str = ""
    docket_number: str = ""

    def to_export_row(self) -> dict[str, str]:
        return {
            "Health Authority": self.health_authority,
            "Guidance Name": self.guidance_name,
            "Summary": self.summary,
            "Issue Date": self.issue_date,
            "FDA Organization": self.fda_organization,
            "Topic": self.topic,
            "Guidance Status": self.guidance_status,
            "Open for Comment": self.open_for_comment,
            "Comment Closing Date on Draft": self.comment_closing_date_on_draft,
            "Guidance PDF Link": self.guidance_pdf_link,
            "Guidance Page Link": self.guidance_page_link,
            "Docket Number": self.docket_number,
        }


def write_csv(records: Iterable[GuidanceRecord], output: TextIO) -> None:
    writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(record.to_export_row())


def write_json(records: Iterable[GuidanceRecord], output: TextIO) -> None:
    payload = [asdict(record) for record in records]
    json.dump(payload, output, indent=2, ensure_ascii=False)
    output.write("\n")
