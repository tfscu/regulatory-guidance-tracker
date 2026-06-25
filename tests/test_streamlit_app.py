import pandas as pd

from app.web.streamlit_app import _filter_by_text, _humanize_label


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
