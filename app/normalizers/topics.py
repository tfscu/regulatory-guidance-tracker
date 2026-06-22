from __future__ import annotations


TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("estimand_and_missing_data", ("estimand", "intercurrent event", "missing data")),
    ("adaptive_design", ("adaptive design",)),
    ("bayesian_methods", ("bayesian",)),
    ("master_protocol", ("master protocol", "platform trial", "basket trial", "umbrella trial")),
    ("external_control", ("external control", "externally controlled")),
    ("real_world_evidence", ("real-world", "real world", "rwe", "rwd")),
    ("vaccine_development", ("vaccine", "vaccines", "疫苗")),
    ("immunogenicity", ("immunogenicity", "免疫原性")),
    ("safety_pharmacovigilance", ("safety", "pharmacovigilance", "安全性")),
    ("pediatric_development", ("pediatric", "paediatric", "儿童", "儿科")),
    ("rare_disease", ("rare disease", "orphan", "罕见病")),
    ("oncology", ("oncology", "cancer", "tumor", "tumour", "肿瘤")),
    ("bioequivalence", ("bioequivalence", "生物等效")),
    ("clinical_pharmacology", ("clinical pharmacology", "pharmacokinetic", "pharmacodynamic")),
    ("CMC_quality", ("cmc", "quality", "manufacturing", "质量")),
    ("nonclinical", ("nonclinical", "non-clinical", "toxicology")),
    ("data_standards", ("data standard", "sdtm", "adam", "define.xml")),
    ("ICH_implementation", ("ich", "step 5", "implementation")),
    ("regulatory_procedure", ("submission", "application", "regulatory procedure", "申报")),
    ("biostatistics", ("biostatistics", "statistical", "statistics", "统计")),
    ("clinical_trial_design", ("clinical trial", "trial design", "study design", "临床试验")),
]


def normalize_topic(title: str, topic_raw: str | None = None, summary: str | None = None) -> str:
    text = f"{title or ''} {topic_raw or ''} {summary or ''}".lower()
    for topic, keywords in TOPIC_RULES:
        if any(keyword.lower() in text for keyword in keywords):
            return topic
    return "other"
