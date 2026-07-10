from datetime import date

import pandas as pd

from app.web.streamlit_app import (
    _detail_metadata,
    _filter_by_text,
    _humanize_label,
    _refresh_status_table,
    _refresh_status_text,
    _selected_export_dataframe,
    _selected_row_indices,
)


def test_humanize_label_formats_status_and_topic_values():
    assert _humanize_label("draft") == "Draft"
    assert _humanize_label("open_for_comment") == "Open for comment"
    assert _humanize_label("CMC_quality") == "CMC Quality"
    assert _humanize_label("safety_pharmacovigilance") == "Safety Pharmacovigilance"


def test_filter_by_text_can_limit_search_to_title_column():
    df = pd.DataFrame(
        [
            {"title": "Adaptive trial guidance", "summary": "Not available."},
            {"title": "Vaccine guidance", "summary": "Adaptive design summary."},
        ]
    )

    filtered = _filter_by_text(df, ["title"], "adaptive")

    assert filtered["title"].tolist() == ["Adaptive trial guidance"]


def test_refresh_status_table_summarizes_last_seen_by_agency():
    df = pd.DataFrame(
        [
            {"agency": "FDA", "last_seen_at": "2026-06-25T01:00:00+00:00"},
            {"agency": "FDA", "last_seen_at": "2026-06-25T03:30:00+00:00"},
            {"agency": "EMA", "last_seen_at": "2026-06-24T09:15:00+00:00"},
        ]
    )

    status = _refresh_status_table(df)

    assert status.to_dict("records") == [
        {"Agency": "EMA", "Records": 1, "Last crawled (UTC)": "2026-06-24 09:15 UTC"},
        {"Agency": "FDA", "Records": 2, "Last crawled (UTC)": "2026-06-25 03:30 UTC"},
    ]

    assert _refresh_status_text(status) == (
        "Last crawled by agency: EMA 2026-06-24 09:15 UTC"
        " | FDA 2026-06-25 03:30 UTC"
    )


def test_selected_export_uses_valid_rows_and_user_facing_columns():
    df = pd.DataFrame(
        [
            {
                "title": "First",
                "agency": "FDA",
                "status_normalized": "final",
                "published_date": date(2025, 1, 1),
                "summary": "Summary one",
                "source_page_url": "https://example.com/first",
                "document_url": "https://example.com/first.pdf",
            },
            {
                "title": "Second",
                "agency": "PMDA",
                "status_normalized": "final",
                "published_date": date(2024, 3, 27),
                "summary": "Summary two",
                "source_page_url": "https://example.com/second",
                "document_url": "https://example.com/second.pdf",
            },
        ]
    )

    selected_rows = _selected_row_indices([1, 99, "0"], len(df))
    exported = _selected_export_dataframe(df, selected_rows)

    assert selected_rows == [1]
    assert exported["title"].tolist() == ["Second"]
    assert "summary" in exported.columns
    assert "last_seen_at" not in exported.columns


def test_detail_metadata_is_compact_and_readable():
    row = pd.Series(
        {
            "agency": "PMDA",
            "status_normalized": "final",
            "published_date": date(2024, 3, 27),
            "topic_normalized": "vaccine_development",
        }
    )

    assert _detail_metadata(row) == (
        "PMDA | Final | Published 2024-03-27 | Vaccine Development"
    )
