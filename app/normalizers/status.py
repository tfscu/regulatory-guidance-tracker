from __future__ import annotations

from datetime import date


ALLOWED_STATUSES = {
    "draft",
    "final",
    "open_for_comment",
    "implemented",
    "withdrawn",
    "superseded",
    "unknown",
}


def normalize_status(
    title: str,
    status_raw: str | None,
    agency: str,
    comment_end_date: date | None = None,
) -> tuple[str, str | None]:
    text = f"{title or ''} {status_raw or ''}".lower()
    agency_key = (agency or "").upper()

    if "superseded" in text:
        return "superseded", None
    if "withdrawn" in text or "废止" in text:
        return "withdrawn", None

    if agency_key == "FDA":
        if "draft" in text and comment_end_date and comment_end_date >= date.today():
            return "open_for_comment", None
        if "draft" in text:
            return "draft", None
        if "final" in text:
            return "final", None

    if agency_key == "EMA":
        if "consultation open" in text or "open consultation" in text:
            return "open_for_comment", None
        if "draft" in text:
            return "draft", None
        if "final" in text or "adopted" in text or "scientific guideline" in text:
            return "final", None

    if agency_key == "ICH":
        if "public consultation" in text or "step 2b" in text:
            return "open_for_comment", None
        if "step 4" in text:
            return "final", None
        if "step 5" in text:
            return "implemented", None

    if agency_key == "CDE":
        if "公开征求" in text or "征求意见稿" in text:
            return "open_for_comment", None
        if "试行" in text:
            return "final", "trial"
        if "发布" in text or "通告" in text:
            return "final", None

    if agency_key == "PMDA":
        if any(marker in text for marker in ("guidance", "guideline", "notification", "regulatory information")):
            return "final", None

    if "open for comment" in text or "consultation" in text:
        return "open_for_comment", None
    if "draft" in text:
        return "draft", None
    if "final" in text:
        return "final", None
    return "unknown", None

