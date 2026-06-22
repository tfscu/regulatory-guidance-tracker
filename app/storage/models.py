from __future__ import annotations

from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class GuidanceDocument(SQLModel, table=True):
    id: str = Field(default="", primary_key=True)
    title: str
    agency: str
    jurisdiction: str
    source_page_url: str | None = None
    document_url: str | None = None
    document_format: str | None = None
    published_date: date | None = None
    updated_date: date | None = None
    comment_start_date: date | None = None
    comment_end_date: date | None = None
    status_raw: str | None = None
    status_normalized: str = "unknown"
    sub_status: str | None = None
    topic_raw: str | None = None
    topic_normalized: str | None = None
    product_area: str | None = None
    summary: str | None = None
    language: str | None = None
    reference_number: str | None = None
    content_hash: str | None = None
    first_seen_at: datetime = Field(default_factory=utc_now)
    last_seen_at: datetime = Field(default_factory=utc_now)
    change_type: str = "unknown"
    needs_manual_review: bool = False
