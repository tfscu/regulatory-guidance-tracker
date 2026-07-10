from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.config import DEFAULT_DB_PATH, bootstrap_database_from_snapshot
from app.storage.repository import GuidanceRepository


st.set_page_config(page_title="Regulatory Guidance Tracker", layout="wide")

SELECTED_EXPORT_COLUMNS = [
    "title",
    "agency",
    "jurisdiction",
    "status_normalized",
    "published_date",
    "updated_date",
    "comment_end_date",
    "topic_normalized",
    "summary",
    "source_page_url",
    "document_url",
]


def main() -> None:
    _apply_styles()
    st.title("Regulatory Guidance Tracker")
    st.caption("ICH, FDA, EMA, CDE, PMDA")

    bootstrap_database_from_snapshot()
    repo = GuidanceRepository(DEFAULT_DB_PATH)
    df = _load_dataframe(repo)
    if df.empty:
        st.info("No records found. Run `python -m app.cli seed` or `python -m app.cli crawl --agency all` first.")
        return

    filtered = _sidebar_filters(df).reset_index(drop=True)
    _metrics(filtered)
    _refresh_status(df)
    selected_rows = _table(filtered)
    _detail_view(filtered, selected_rows[0] if selected_rows else 0)


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
                "last_seen_at": doc.last_seen_at,
            }
        )
    return pd.DataFrame(rows)


def _sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    filtered = df.copy()

    agency = st.sidebar.multiselect("Agency", sorted(df["agency"].dropna().unique()))
    if agency:
        filtered = filtered[filtered["agency"].isin(agency)]

    status = st.sidebar.multiselect(
        "Status",
        sorted(df["status_normalized"].dropna().unique()),
        format_func=_humanize_label,
    )
    if status:
        filtered = filtered[filtered["status_normalized"].isin(status)]

    topic = st.sidebar.multiselect(
        "Topic",
        sorted(df["topic_normalized"].dropna().unique()),
        format_func=_humanize_label,
    )
    if topic:
        filtered = filtered[filtered["topic_normalized"].isin(topic)]

    keyword = st.sidebar.text_input("Keyword search")
    if keyword:
        filtered = _filter_by_text(
            filtered,
            ["title", "summary", "topic_normalized", "agency"],
            keyword,
        )

    title_query = st.sidebar.text_input("Title search")
    if title_query:
        filtered = _filter_by_text(filtered, ["title"], title_query)

    min_date, max_date = _date_bounds(df)
    if min_date and max_date:
        selected_range = st.sidebar.date_input("Published date range", value=(min_date, max_date))
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start, end = selected_range
            filtered = filtered[
                filtered["published_date"].isna()
                | ((filtered["published_date"] >= start) & (filtered["published_date"] <= end))
            ]

    return filtered


def _filter_by_text(df: pd.DataFrame, columns: list[str], query: str) -> pd.DataFrame:
    lowered_query = query.lower()
    corpus = pd.Series("", index=df.index)
    for column in columns:
        corpus = corpus + " " + df[column].fillna("").astype(str)
    return df[corpus.str.lower().str.contains(lowered_query, regex=False)]


def _date_bounds(df: pd.DataFrame) -> tuple[date | None, date | None]:
    dates = [value for value in df["published_date"].dropna().tolist() if isinstance(value, date)]
    if not dates:
        return None, None
    return min(dates), max(dates)


def _metrics(df: pd.DataFrame) -> None:
    metrics = st.container(key="metrics")
    total, final, draft, open_comment = metrics.columns(4)
    total.metric("Total documents", len(df))
    final.metric("Final documents", int((df["status_normalized"] == "final").sum()))
    draft.metric("Draft documents", int((df["status_normalized"] == "draft").sum()))
    open_comment.metric("Open for comment", int((df["status_normalized"] == "open_for_comment").sum()))


def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1200px;
            padding-top: 3rem;
        }
        @media (max-width: 640px) {
            .block-container {
                padding-top: 2rem;
            }
            h1 {
                font-size: 2rem !important;
                line-height: 1.15 !important;
            }
            .st-key-metrics [data-testid="stHorizontalBlock"] {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.75rem 1rem;
            }
            .st-key-metrics [data-testid="column"] {
                width: auto !important;
                min-width: 0 !important;
                flex: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _refresh_status(df: pd.DataFrame) -> None:
    status = _refresh_status_table(df)
    if status.empty:
        return
    st.caption(_refresh_status_text(status))


def _refresh_status_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "last_seen_at" not in df.columns:
        return pd.DataFrame(columns=["Agency", "Records", "Last crawled (UTC)"])

    rows = []
    for agency, group in df.groupby("agency", dropna=True):
        seen_values = [_parse_datetime(value) for value in group["last_seen_at"].dropna()]
        last_seen = max((value for value in seen_values if value is not None), default=None)
        rows.append(
            {
                "Agency": agency,
                "Records": len(group),
                "Last crawled (UTC)": _format_refresh_time(last_seen),
            }
        )
    return pd.DataFrame(rows).sort_values("Agency").reset_index(drop=True)


def _refresh_status_text(status: pd.DataFrame) -> str:
    items = [
        f"{row['Agency']} {row['Last crawled (UTC)']}"
        for row in status.to_dict("records")
    ]
    return "Last crawled by agency: " + " | ".join(items)


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_refresh_time(value: datetime | None) -> str:
    if value is None:
        return "Not available."
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _table(df: pd.DataFrame) -> list[int]:
    st.subheader("Guidance documents")
    toolbar = st.container(horizontal=True, vertical_alignment="center", gap="small")
    export_slot = toolbar.empty()
    selection_slot = toolbar.empty()
    table_df = df.assign(
        status_display=df["status_normalized"].map(_humanize_label),
        topic_display=df["topic_normalized"].map(_humanize_label),
    )
    columns = [
        "title",
        "agency",
        "status_display",
        "published_date",
        "topic_display",
        "source_page_url",
        "document_url",
    ]
    event = st.dataframe(
        table_df[columns],
        width="stretch",
        height=600,
        row_height=44,
        hide_index=True,
        key="guidance_documents_table",
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "title": st.column_config.TextColumn("Title", width=320, pinned=True),
            "agency": st.column_config.TextColumn("Agency", width=65),
            "status_display": st.column_config.TextColumn("Status", width=115),
            "published_date": st.column_config.DateColumn("Published", width=105),
            "topic_display": st.column_config.TextColumn("Topic", width=135),
            "source_page_url": st.column_config.LinkColumn(
                "Source",
                width=60,
                display_text=":material/open_in_new:",
                help="Open the official source page",
            ),
            "document_url": st.column_config.LinkColumn(
                "PDF",
                width=60,
                display_text=":material/picture_as_pdf:",
                help="Open the guidance document",
            ),
        },
    )
    selected_rows = _selected_row_indices(
        getattr(getattr(event, "selection", None), "rows", []),
        len(df),
    )
    selected_export = _selected_export_dataframe(df, selected_rows)
    export_slot.download_button(
        "Export selected CSV",
        data=selected_export.to_csv(index=False).encode("utf-8-sig"),
        file_name="selected_regulatory_guidance.csv",
        mime="text/csv",
        icon=":material/download:",
        disabled=selected_export.empty,
        on_click="ignore",
    )
    selection_slot.caption(f"{len(selected_rows)} selected")
    return selected_rows


def _selected_row_indices(rows: object, row_count: int) -> list[int]:
    if not isinstance(rows, (list, tuple)):
        return []
    return [index for value in rows if isinstance(value, int) and 0 <= (index := int(value)) < row_count]


def _selected_export_dataframe(df: pd.DataFrame, selected_rows: list[int]) -> pd.DataFrame:
    columns = [column for column in SELECTED_EXPORT_COLUMNS if column in df.columns]
    if not selected_rows:
        return pd.DataFrame(columns=columns)
    return df.iloc[selected_rows][columns].reset_index(drop=True)


def _detail_view(df: pd.DataFrame, selected_row: int) -> None:
    st.subheader("Detail view")
    if df.empty:
        st.write("No document selected.")
        return
    row = df.iloc[min(selected_row, len(df) - 1)]
    st.markdown(f"### {row['title']}")
    st.caption(_detail_metadata(row))
    st.write(_display_value(row["summary"]))
    source_page_url = _clean_url(row["source_page_url"])
    document_url = _clean_url(row["document_url"])
    actions = st.container(horizontal=True, gap="small")
    if source_page_url:
        actions.link_button("Source page", source_page_url, icon=":material/open_in_new:")
    else:
        actions.caption("Source page not available")
    if document_url:
        actions.link_button("Document", document_url, icon=":material/picture_as_pdf:")
    else:
        actions.caption("Document not available")


def _detail_metadata(row: pd.Series) -> str:
    published = _display_value(row.get("published_date"))
    values = [
        _display_value(row.get("agency")),
        _humanize_label(row.get("status_normalized")),
        f"Published {published}",
        _humanize_label(row.get("topic_normalized")),
    ]
    return " | ".join(values)


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
