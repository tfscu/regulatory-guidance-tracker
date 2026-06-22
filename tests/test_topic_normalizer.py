from app.normalizers.topics import normalize_topic


def test_topic_keyword_rules():
    assert normalize_topic("Estimand and missing data in clinical trials") == "estimand_and_missing_data"
    assert normalize_topic("Adaptive design for clinical trials") == "adaptive_design"
    assert normalize_topic("Bayesian methods in drug development") == "bayesian_methods"
    assert normalize_topic("Master protocol platform trial guidance") == "master_protocol"
    assert normalize_topic("Externally controlled trial considerations") == "external_control"
    assert normalize_topic("Real-world evidence and RWD guidance") == "real_world_evidence"
    assert normalize_topic("Clinical evaluation of vaccines") == "vaccine_development"
    assert normalize_topic("Immunogenicity assay considerations") == "immunogenicity"
    assert normalize_topic("Safety pharmacovigilance planning") == "safety_pharmacovigilance"
    assert normalize_topic("Pediatric study planning") == "pediatric_development"
    assert normalize_topic("Statistical principles for clinical trials") == "biostatistics"


def test_topic_falls_back_to_other():
    assert normalize_topic("Administrative contacts") == "other"

