from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from sqlmodel import Session, delete, select

from app.config import DEFAULT_DB_PATH
from app.storage.db import get_session, init_db
from app.storage.models import GuidanceDocument


CHANGE_FIELDS = (
    "title",
    "status_normalized",
    "published_date",
    "updated_date",
    "document_url",
    "summary",
)


def stable_document_id(document: GuidanceDocument) -> str:
    locator = document.source_page_url or document.document_url or ""
    key = f"{document.agency}|{document.title.strip().lower()}|{locator.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def content_hash(document: GuidanceDocument) -> str:
    parts = [
        document.title,
        document.status_normalized,
        str(document.published_date or ""),
        str(document.updated_date or ""),
        document.document_url or "",
        document.summary or "",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


class GuidanceRepository:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def save(self, document: GuidanceDocument) -> GuidanceDocument:
        with get_session(self.db_path) as session:
            return self._save_in_session(session, document)

    def save_many(self, documents: Iterable[GuidanceDocument]) -> list[GuidanceDocument]:
        saved: list[GuidanceDocument] = []
        with get_session(self.db_path) as session:
            for document in documents:
                saved.append(self._save_in_session(session, document))
            session.commit()
            for document in saved:
                session.refresh(document)
        return saved

    def list_documents(self) -> list[GuidanceDocument]:
        with get_session(self.db_path) as session:
            return list(session.exec(select(GuidanceDocument)).all())

    def delete_by_agency(self, agency: str) -> int:
        agency_key = agency.upper()
        with get_session(self.db_path) as session:
            documents = list(session.exec(select(GuidanceDocument).where(GuidanceDocument.agency == agency_key)).all())
            count = len(documents)
            session.exec(delete(GuidanceDocument).where(GuidanceDocument.agency == agency_key))
            session.commit()
            return count

    def _save_in_session(self, session: Session, document: GuidanceDocument) -> GuidanceDocument:
        now = datetime.now(UTC)
        document.id = document.id or stable_document_id(document)
        document.content_hash = content_hash(document)
        existing = session.get(GuidanceDocument, document.id)

        if existing is None:
            document.change_type = "new"
            document.first_seen_at = now
            document.last_seen_at = now
            session.add(document)
            session.commit()
            session.refresh(document)
            return document

        changed = any(getattr(existing, field) != getattr(document, field) for field in CHANGE_FIELDS)
        field_names = getattr(GuidanceDocument, "model_fields", None) or getattr(GuidanceDocument, "__fields__")
        for field in field_names:
            if field in {"id", "first_seen_at"}:
                continue
            setattr(existing, field, getattr(document, field))
        existing.change_type = "updated" if changed else "unchanged"
        existing.first_seen_at = existing.first_seen_at
        existing.last_seen_at = now
        existing.content_hash = content_hash(existing)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
