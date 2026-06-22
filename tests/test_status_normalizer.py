from datetime import date

from app.normalizers.status import normalize_status


def test_fda_draft_with_future_comment_date_is_open_for_comment():
    status, sub_status = normalize_status("Example Draft Guidance", "Draft", "FDA", date(2099, 1, 1))

    assert status == "open_for_comment"
    assert sub_status is None


def test_fda_final_maps_to_final():
    status, _ = normalize_status("Example Final Guidance", "Final", "FDA")

    assert status == "final"


def test_ema_open_consultation_maps_to_open_for_comment():
    status, _ = normalize_status("Open consultation on RWE", "Consultation open", "EMA")

    assert status == "open_for_comment"


def test_ich_step_rules():
    assert normalize_status("ICH E20", "Step 2b public consultation", "ICH")[0] == "open_for_comment"
    assert normalize_status("ICH E9", "Step 4", "ICH")[0] == "final"
    assert normalize_status("ICH E6", "Step 5", "ICH")[0] == "implemented"


def test_cde_chinese_rules():
    assert normalize_status("关于公开征求疫苗指导原则意见的通知", None, "CDE")[0] == "open_for_comment"
    assert normalize_status("关于发布药物临床试验指导原则的通告", None, "CDE")[0] == "final"
    assert normalize_status("药物临床试验指导原则（试行）", None, "CDE") == ("final", "trial")
    assert normalize_status("关于废止某指导原则的公告", None, "CDE")[0] == "withdrawn"


def test_pmda_guidance_defaults_to_final():
    status, _ = normalize_status("Regulatory information guidance for clinical trials", None, "PMDA")

    assert status == "final"

