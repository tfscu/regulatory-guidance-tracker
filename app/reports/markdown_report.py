from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.config import EXPORT_DIR, HIGH_PRIORITY_TOPICS
from app.storage.models import GuidanceDocument


DEFAULT_REPORT_PATH = EXPORT_DIR / "regulatory_update_report.md"


WHY_IT_MATTERS = {
    "biostatistics": "Directly relevant to statistical design, analysis, or review.",
    "clinical_trial_design": "May affect endpoint, population, comparator, or study design decisions.",
    "estimand_and_missing_data": "Important for estimand strategy, intercurrent events, and sensitivity analyses.",
    "adaptive_design": "May affect interim decision rules and operating characteristics.",
    "bayesian_methods": "Relevant to Bayesian borrowing, priors, and decision criteria.",
    "master_protocol": "Relevant to platform, basket, umbrella, or other complex trial structures.",
    "external_control": "Important for externally controlled trial evidence planning.",
    "real_world_evidence": "Relevant to RWE/RWD evidence generation and regulatory acceptability.",
    "vaccine_development": "Directly relevant to vaccine clinical development.",
    "immunogenicity": "Relevant to immune response endpoints and assay interpretation.",
    "safety_pharmacovigilance": "Relevant to safety monitoring and risk management.",
}


def generate_markdown_report(
    documents: list[GuidanceDocument],
    output_path: Path = DEFAULT_REPORT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_docs = [doc for doc in documents if doc.change_type == "new"]
    updated_docs = [doc for doc in documents if doc.change_type == "updated"]
    open_docs = [doc for doc in documents if doc.status_normalized == "open_for_comment"]
    high_priority_docs = [doc for doc in documents if doc.topic_normalized in HIGH_PRIORITY_TOPICS]

    lines = [
        "# Regulatory Guidance Update Report",
        f"Generated at: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Executive Summary",
        f"- Total documents: {len(documents)}",
        f"- New documents: {len(new_docs)}",
        f"- Updated documents: {len(updated_docs)}",
        f"- Open for comment: {len(open_docs)}",
        f"- High-priority documents: {len(high_priority_docs)}",
        "",
        "## New Guidance",
        "| Agency | Title | Status | Date | Topic | Link |",
        "|---|---|---|---|---|---|",
        *[_guidance_row(doc) for doc in new_docs],
        "",
        "## Open for Comment",
        "| Agency | Title | Comment End Date | Topic | Link |",
        "|---|---|---|---|---|",
        *[_open_comment_row(doc) for doc in open_docs],
        "",
        "## High Priority for Biostatistics / Vaccine Clinical Development",
        "| Agency | Title | Status | Topic | Why it matters |",
        "|---|---|---|---|---|",
        *[_priority_row(doc) for doc in high_priority_docs],
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _guidance_row(doc: GuidanceDocument) -> str:
    return (
        f"| {doc.agency} | {_escape(doc.title)} | {doc.status_normalized} | "
        f"{doc.published_date or ''} | {doc.topic_normalized or ''} | {_link(doc)} |"
    )


def _open_comment_row(doc: GuidanceDocument) -> str:
    return (
        f"| {doc.agency} | {_escape(doc.title)} | {doc.comment_end_date or ''} | "
        f"{doc.topic_normalized or ''} | {_link(doc)} |"
    )


def _priority_row(doc: GuidanceDocument) -> str:
    why = WHY_IT_MATTERS.get(doc.topic_normalized or "", "Potentially relevant to clinical development review.")
    return f"| {doc.agency} | {_escape(doc.title)} | {doc.status_normalized} | {doc.topic_normalized or ''} | {_escape(why)} |"


def _link(doc: GuidanceDocument) -> str:
    url = doc.document_url or doc.source_page_url or ""
    return f"[Link]({url})" if url else ""


def _escape(value: str) -> str:
    return value.replace("|", "\\|")

