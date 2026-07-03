import pandas as pd

from app.web.streamlit_app import _filter_by_text, _humanize_label, _refresh_status_table


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
