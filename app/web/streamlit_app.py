from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.config import DEFAULT_DB_PATH
from app.storage.repository import GuidanceRepository


st.set_page_config(page_title="Regulatory Guidance Tracker", layout="wide")


def main() -> None:
    st.title("Regulatory Guidance Tracker")
    st.caption("ICH, FDA, EMA, CDE, NMPA")

    repo = GuidanceRepository(DEFAULT_DB_PATH)
    df = _load_dataframe(repo)
    if df.empty:
        st.info("No records found. Run `python -m app.cli seed` or `python -m app.cli crawl --agency all` first.")
        return

    filtered = _sidebar_filters(df).reset_index(drop=True)
    _metrics(filtered)
    selected_row = _table(filtered)
    _detail_view(filtered, selected_row)


def _load_dataframe(repo: GuidanceRepository) -> pd.DataFrame:
    rows = []
    for doc in repo.list_documents():
        rows.append(
            {
                "title": doc.title,
                "agency": doc.agency,
                "jurisdiction": doc.jurisdiction,
                "status_normalized": doc.status_normalized,
                "published_date": doc.published_date,
                "updated_date": doc.updated_date,
                "comment_end_date": doc.comment_end_date,
                "topic_normalized": doc.topic_normalized,
                "summary": doc.summary,
                "document_url": doc.document_url,
                "source_page_url": doc.source_page_url,
                "change_type": doc.change_type,
                "needs_manual_review": doc.needs_manual_review,
            }
        )
    return pd.DataFrame(rows)


def _sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    filtered = df.copy()

    agency = st.sidebar.multiselect("Agency", sorted(df["agency"].dropna().unique()))
    if agency:
        filtered = filtered[filtered["agency"].isin(agency)]

    status = st.sidebar.multiselect("Status", sorted(df["status_normalized"].dropna().unique()))
    if status:
        filtered = filtered[filtered["status_normalized"].isin(status)]

    topic = st.sidebar.multiselect("Topic", sorted(df["topic_normalized"].dropna().unique()))
    if topic:
        filtered = filtered[filtered["topic_normalized"].isin(topic)]

    min_date, max_date = _date_bounds(df)
    if min_date and max_date:
        selected_range = st.sidebar.date_input("Published date range", value=(min_date, max_date))
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start, end = selected_range
            filtered = filtered[
                filtered["published_date"].isna()
                | ((filtered["published_date"] >= start) & (filtered["published_date"] <= end))
            ]

    keyword = st.sidebar.text_input("Keyword search")
    if keyword:
        query = keyword.lower()
        corpus = (
            filtered["title"].fillna("")
            + " "
            + filtered["summary"].fillna("")
            + " "
            + filtered["topic_normalized"].fillna("")
            + " "
            + filtered["agency"].fillna("")
        ).str.lower()
        filtered = filtered[corpus.str.contains(query, regex=False)]

    return filtered


def _date_bounds(df: pd.DataFrame) -> tuple[date | None, date | None]:
    dates = [value for value in df["published_date"].dropna().tolist() if isinstance(value, date)]
    if not dates:
        return None, None
    return min(dates), max(dates)


def _metrics(df: pd.DataFrame) -> None:
    total, final, draft, open_comment = st.columns(4)
    total.metric("Total documents", len(df))
    final.metric("Final documents", int((df["status_normalized"] == "final").sum()))
    draft.metric("Draft documents", int((df["status_normalized"] == "draft").sum()))
    open_comment.metric("Open for comment", int((df["status_normalized"] == "open_for_comment").sum()))


def _table(df: pd.DataFrame) -> int:
    st.subheader("Guidance documents")
    table_df = df.assign(
        status_display=df["status_normalized"].map(_humanize_label),
        topic_display=df["topic_normalized"].map(_humanize_label),
    )
    columns = [
        "title",
        "agency",
        "status_display",
        "published_date",
        "updated_date",
        "topic_display",
        "source_page_url",
        "document_url",
    ]
    event = st.dataframe(
        table_df[columns],
        use_container_width=True,
        hide_index=True,
        key="guidance_documents_table",
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "title": st.column_config.TextColumn("Title"),
            "agency": st.column_config.TextColumn("Agency"),
            "status_display": st.column_config.TextColumn("Status"),
            "published_date": st.column_config.DateColumn("Published date"),
            "updated_date": st.column_config.DateColumn("Updated date"),
            "topic_display": st.column_config.TextColumn("Topic"),
            "source_page_url": st.column_config.LinkColumn("Source page"),
            "document_url": st.column_config.LinkColumn("PDF"),
        },
    )
    selected_rows = getattr(getattr(event, "selection", None), "rows", [])
    if selected_rows:
        return int(selected_rows[0])
    return 0


def _detail_view(df: pd.DataFrame, selected_row: int) -> None:
    st.subheader("Detail view")
    if df.empty:
        st.write("No document selected.")
        return
    row = df.iloc[min(selected_row, len(df) - 1)]
    st.markdown(f"### {row['title']}")
    st.write(_display_value(row["summary"]))
    source_page_url = _clean_url(row["source_page_url"])
    document_url = _clean_url(row["document_url"])
    if source_page_url:
        st.link_button("Source page", source_page_url)
    else:
        st.write("Source page: Not available.")
    if document_url:
        st.link_button("Document", document_url)
    else:
        st.write("Document: Not available.")


def _display_value(value: object) -> str:
    if pd.isna(value) or not str(value).strip():
        return "Not available."
    return str(value)


def _humanize_label(value: object) -> str:
    text = _display_value(value)
    if text == "Not available.":
        return text
    phrases = {"open_for_comment": "Open for comment"}
    if text in phrases:
        return phrases[text]
    acronyms = {"CMC", "FDA", "EMA", "ICH", "CDE", "NMPA", "PMDA", "RWE", "RWD", "MIDD"}
    small_words = {"and", "for", "in", "of", "on", "or", "the", "to", "with"}
    words = text.replace("_", " ").split()
    formatted = []
    for index, word in enumerate(words):
        upper = word.upper()
        lower = word.lower()
        if upper in acronyms:
            formatted.append(upper)
        elif index > 0 and lower in small_words:
            formatted.append(lower)
        else:
            formatted.append(lower.capitalize())
    return " ".join(formatted)


def _clean_url(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text or text.lower() == "none":
        return ""
    return text


if __name__ == "__main__":
    main()
