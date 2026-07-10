from __future__ import annotations

from app.normalizers.dates import parse_date
from app.normalizers.status import normalize_status
from app.normalizers.topics import normalize_topic
from app.storage.models import GuidanceDocument


SEED_ROWS = [
    {
        "title": "Adaptive Designs for Clinical Trials of Drugs and Biologics",
        "agency": "FDA",
        "jurisdiction": "US",
        "status_raw": "Final",
        "published_date": "2019-11-01",
        "topic_raw": "Clinical Trials",
        "summary": "[Seed/demo data] FDA guidance example for adaptive clinical trial design.",
        "source_page_url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
    },
    {
        "title": "E9(R1) Statistical Principles for Clinical Trials: Addendum on Estimands and Sensitivity Analysis",
        "agency": "ICH",
        "jurisdiction": "International",
        "status_raw": "Step 4",
        "published_date": "2019-11-20",
        "topic_raw": "Biostatistics",
        "summary": "[Seed/demo data] ICH estimand and missing data guidance relevant to trial objectives.",
        "source_page_url": "https://www.ich.org/page/efficacy-guidelines",
    },
    {
        "title": "ICH E20 Adaptive Clinical Trials - Public Consultation",
        "agency": "ICH",
        "jurisdiction": "International",
        "status_raw": "Step 2b public consultation",
        "published_date": "2025-05-15",
        "comment_end_date": "2025-08-15",
        "topic_raw": "Adaptive Design",
        "summary": "[Seed/demo data] Public consultation example for adaptive clinical trials.",
        "source_page_url": "https://www.ich.org/page/public-consultations",
    },
    {
        "title": "Guideline on clinical evaluation of vaccines",
        "agency": "EMA",
        "jurisdiction": "EU",
        "status_raw": "Scientific guideline adopted",
        "published_date": "2023-02-10",
        "topic_raw": "Vaccines",
        "summary": "[Seed/demo data] EMA vaccine clinical development guidance example.",
        "source_page_url": "https://www.ema.europa.eu/en/human-regulatory-overview/research-development/scientific-guidelines",
    },
    {
        "title": "Open consultation on real-world evidence for medicines development",
        "agency": "EMA",
        "jurisdiction": "EU",
        "status_raw": "Consultation open",
        "published_date": "2026-01-10",
        "comment_end_date": "2026-09-30",
        "topic_raw": "Real World Evidence",
        "summary": "[Seed/demo data] EMA open consultation example for RWE/RWD.",
        "source_page_url": "https://www.ema.europa.eu/en/news-events/open-consultations",
    },
    {
        "title": "关于公开征求疫苗临床试验技术指导原则意见的通知",
        "agency": "CDE",
        "jurisdiction": "China",
        "status_raw": "公开征求意见",
        "published_date": "2026-03-01",
        "comment_end_date": "2026-07-01",
        "topic_raw": "疫苗 临床试验",
        "summary": "[Seed/demo data] CDE vaccine clinical trial consultation example.",
        "language": "ZH",
        "source_page_url": "https://www.cde.org.cn/",
    },
    {
        "title": "关于发布药物临床试验统计学指导原则的通告",
        "agency": "CDE",
        "jurisdiction": "China",
        "status_raw": "发布 通告",
        "published_date": "2024-10-20",
        "topic_raw": "统计 临床试验",
        "summary": "[Seed/demo data] CDE biostatistics guidance example.",
        "language": "ZH",
        "source_page_url": "https://www.cde.org.cn/",
    },
    {
        "title": "Pediatric Development of Vaccines",
        "agency": "FDA",
        "jurisdiction": "US",
        "status_raw": "Draft",
        "published_date": "2026-02-01",
        "comment_end_date": "2026-10-01",
        "topic_raw": "Vaccines",
        "summary": "[Seed/demo data] Draft vaccine pediatric development guidance example.",
        "source_page_url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
    },
    {
        "title": "Use of Bayesian Methods in Medical Product Development",
        "agency": "FDA",
        "jurisdiction": "US",
        "status_raw": "Final",
        "published_date": "2022-12-01",
        "topic_raw": "Biostatistics",
        "summary": "[Seed/demo data] Bayesian methods example for statistical review.",
        "source_page_url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
    },
]


def seed_documents(agencies: set[str] | None = None) -> list[GuidanceDocument]:
    documents: list[GuidanceDocument] = []
    wanted = {agency.upper() for agency in agencies} if agencies else None
    for row in SEED_ROWS:
        if wanted and row["agency"].upper() not in wanted:
            continue
        published_date = parse_date(row.get("published_date"))
        comment_end_date = parse_date(row.get("comment_end_date"))
        status, sub_status = normalize_status(
            row["title"],
            row.get("status_raw"),
            row["agency"],
            comment_end_date=comment_end_date,
        )
        topic = normalize_topic(row["title"], row.get("topic_raw"), row.get("summary"))
        documents.append(
            GuidanceDocument(
                title=row["title"],
                agency=row["agency"],
                jurisdiction=row["jurisdiction"],
                source_page_url=row.get("source_page_url"),
                document_url=row.get("document_url"),
                document_format=row.get("document_format"),
                published_date=published_date,
                comment_end_date=comment_end_date,
                status_raw=row.get("status_raw"),
                status_normalized=status,
                sub_status=sub_status,
                topic_raw=row.get("topic_raw"),
                topic_normalized=topic,
                product_area=row.get("product_area"),
                summary=row.get("summary"),
                language=row.get("language", "EN"),
                reference_number=row.get("reference_number"),
                needs_manual_review=True,
            )
        )
    return documents
