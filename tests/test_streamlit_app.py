from app.web.streamlit_app import _humanize_label


def test_humanize_label_formats_status_and_topic_values():
    assert _humanize_label("draft") == "Draft"
    assert _humanize_label("open_for_comment") == "Open for comment"
    assert _humanize_label("CMC_quality") == "CMC Quality"
    assert _humanize_label("safety_pharmacovigilance") == "Safety Pharmacovigilance"
