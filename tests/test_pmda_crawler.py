from datetime import date

import pytest

from app.crawlers.pmda import (
    PMDA_CLINICAL_TRIALS_URL,
    PMDA_SOURCES,
    PMDA_VACCINES_URL,
    PMDACrawler,
    parse_pmda_guidance_html,
    parse_pmda_pages,
)
from app.crawlers import crawler_for_agency


CLINICAL_HTML = """
<main>
  <h2>Regulations and Notifications</h2>
  <h4>First in Human Studies</h4>
  <ul><li><a href="/files/000153028.pdf">First-in-Human Guidance[263.18KB]</a></li></ul>
  <p>April 18, 2012 PFSB/ELD Administrative Notice</p>
  <h4>Clinical Trial Notification Review</h4>
  <ul><li><a href="/files/000274534.pdf">Mutagenic Impurities (Early Consideration)［399KB］</a><br>
  January 16, 2025 Administrative Notice</li></ul>
  <h2>Frequently Asked Questions (FAQ)</h2>
  <a href="/files/excluded.pdf">Not a guidance record</a>
</main>
"""


VACCINE_HTML = """
<main>
  <h2>Regulations and Notifications</h2>
  <h3>Vaccines for Infectious Disease</h3>
  <h4>Non-Clinical Studies</h4>
  <ul><li><a href="/files/nonclinical.pdf">Excluded nonclinical vaccine guidance [100KB]</a></li></ul>
  <p>March 27, 2024 Administrative Notice</p>
  <h4>Clinical Studies</h4>
  <ul><li><a href="/files/000279487.pdf">Guidelines for Clinical Studies of Vaccines [201.06KB]</a></li></ul>
  <p>March 27, 2024 PSB/PED Notification No. 0327-4</p>
  <h4>Prototype Vaccines</h4>
  <ul><li><a href="/files/000280546.pdf">Prototype Vaccine Guideline [215KB]</a></li></ul>
  <p>October 31, 2011 PFSB/ELD Notification No. 1031-1</p>
  <h4>Vaccines Against the Novel Coronavirus SARS-CoV-2</h4>
  <ul><li><a href="/files/000237021.pdf">Principles for Evaluation of SARS-CoV-2 Vaccines [387.83KB]</a></li></ul>
  <p>September 2, 2020 Office of Vaccines and Blood Products</p>
  <h3>Blood Products</h3>
  <h4>Human Immunoglobulin Products</h4>
  <ul><li><a href="/files/blood.pdf">Excluded blood product guidance [100KB]</a></li></ul>
</main>
"""


def test_parse_pmda_clinical_page_extracts_metadata_and_pdf():
    documents = parse_pmda_guidance_html(CLINICAL_HTML, PMDA_SOURCES[0])

    assert len(documents) == 2
    first = documents[0]
    assert first.title == "First-in-Human Guidance"
    assert first.agency == "PMDA"
    assert first.jurisdiction == "Japan"
    assert first.document_url == "https://www.pmda.go.jp/files/000153028.pdf"
    assert first.document_format == "PDF"
    assert first.published_date == date(2012, 4, 18)
    assert first.status_raw == "PFSB/ELD Administrative Notice"
    assert first.status_normalized == "final"
    assert first.product_area == "Drug clinical trials"
    assert first.summary == "Not available."
    assert first.reference_number == "000153028"
    assert first.needs_manual_review is False

    assert documents[1].published_date == date(2025, 1, 16)
    assert documents[1].sub_status == "early_consideration"


def test_parse_pmda_vaccine_page_keeps_only_requested_sections():
    documents = parse_pmda_guidance_html(VACCINE_HTML, PMDA_SOURCES[1])

    assert [document.reference_number for document in documents] == [
        "000279487",
        "000280546",
        "000237021",
    ]
    assert all(document.product_area == "Vaccines" for document in documents)
    assert all(document.topic_normalized == "vaccine_development" for document in documents)
    assert all(document.status_normalized == "final" for document in documents)
    assert all("Excluded" not in document.title for document in documents)


def test_parse_pmda_pages_requires_every_source_and_deduplicates_urls():
    pages = {
        PMDA_CLINICAL_TRIALS_URL: CLINICAL_HTML,
        PMDA_VACCINES_URL: VACCINE_HTML.replace(
            "/files/000279487.pdf", "/files/000153028.pdf"
        ),
    }

    documents = parse_pmda_pages(pages)

    assert len(documents) == 4
    assert len({document.document_url for document in documents}) == 4

    with pytest.raises(ValueError, match="missing required source page"):
        parse_pmda_pages({PMDA_CLINICAL_TRIALS_URL: CLINICAL_HTML})


def test_pmda_crawler_uses_injected_fetcher():
    crawler = PMDACrawler(
        fetch_pages=lambda: {
            PMDA_CLINICAL_TRIALS_URL: CLINICAL_HTML,
            PMDA_VACCINES_URL: VACCINE_HTML,
        }
    )

    documents = crawler.crawl()

    assert len(documents) == 5


def test_pmda_crawler_is_registered():
    assert isinstance(crawler_for_agency("PMDA"), PMDACrawler)
