from __future__ import annotations

import csv
import logging
from pathlib import Path

import typer

from app.config import DEFAULT_DB_PATH, EXPORT_DIR, ensure_data_dirs
from app.crawlers import configured_agencies, crawler_for_agency
from app.reports.markdown_report import DEFAULT_REPORT_PATH, generate_markdown_report
from app.seed import seed_documents
from app.storage.db import init_db
from app.storage.models import GuidanceDocument
from app.storage.repository import GuidanceRepository


app = typer.Typer(help="Regulatory Guidance Tracker CLI")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


@app.command("init-db")
def init_db_command(db_path: Path = DEFAULT_DB_PATH) -> None:
    ensure_data_dirs()
    init_db(db_path)
    typer.echo(f"Initialized SQLite database at {db_path}")


@app.command()
def seed(db_path: Path = DEFAULT_DB_PATH) -> None:
    repo = GuidanceRepository(db_path)
    saved = repo.save_many(seed_documents())
    typer.echo(f"Saved {len(saved)} seed/demo guidance records.")


@app.command()
def crawl(
    agency: str = typer.Option("all", "--agency", "-a", help="Agency to crawl: all, FDA, EMA, ICH, CDE, PMDA."),
    max_records: int = typer.Option(50, help="Maximum FDA records for the MVP crawl."),
    all_records: bool = typer.Option(False, help="Crawl all available records for supported agencies."),
    seed_if_empty: bool = typer.Option(True, help="Load seed/demo records for agencies with no crawler results."),
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    repo = GuidanceRepository(db_path)
    agencies = configured_agencies() if agency.lower() == "all" else [agency.upper()]
    crawled: list[GuidanceDocument] = []

    for agency_name in agencies:
        try:
            crawler = crawler_for_agency(agency_name)
            if agency_name == "FDA":
                crawler.max_records = None if all_records else max_records
            crawled.extend(crawler.crawl())
        except Exception as exc:
            logging.warning("%s crawler failed and was skipped: %s", agency_name, exc)

    crawled_agencies = {doc.agency.upper() for doc in crawled}
    if seed_if_empty:
        missing_agencies = {item.upper() for item in agencies} - crawled_agencies
        if missing_agencies:
            crawled.extend(seed_documents(missing_agencies))

    saved = repo.save_many(crawled)
    typer.echo(f"Saved {len(saved)} guidance records.")


@app.command("export-csv")
def export_csv(
    output: Path = EXPORT_DIR / "regulatory_guidance.csv",
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    repo = GuidanceRepository(db_path)
    documents = repo.list_documents()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_export_columns())
        writer.writeheader()
        for document in documents:
            writer.writerow(_document_row(document))
    typer.echo(f"Wrote {len(documents)} records to {output}")


@app.command("generate-report")
def generate_report(
    output: Path = DEFAULT_REPORT_PATH,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    repo = GuidanceRepository(db_path)
    path = generate_markdown_report(repo.list_documents(), output)
    typer.echo(f"Wrote Markdown report to {path}")


@app.command("run-web")
def run_web() -> None:
    typer.echo("Run the web app with:")
    typer.echo("streamlit run app/web/streamlit_app.py")


def _export_columns() -> list[str]:
    return [
        "id",
        "title",
        "agency",
        "jurisdiction",
        "source_page_url",
        "document_url",
        "document_format",
        "published_date",
        "updated_date",
        "comment_start_date",
        "comment_end_date",
        "status_raw",
        "status_normalized",
        "sub_status",
        "topic_raw",
        "topic_normalized",
        "product_area",
        "summary",
        "language",
        "reference_number",
        "content_hash",
        "first_seen_at",
        "last_seen_at",
        "change_type",
        "needs_manual_review",
    ]


def _document_row(document: GuidanceDocument) -> dict[str, str]:
    return {column: str(getattr(document, column) or "") for column in _export_columns()}


if __name__ == "__main__":
    app()
