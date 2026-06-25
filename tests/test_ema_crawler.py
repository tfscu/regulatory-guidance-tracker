from datetime import date

from app.crawlers.ema import (
    EMACrawler,
    _parse_ema_date,
    enrich_ema_documents_with_pdf_links,
    extract_ema_pdf_url_from_html,
    parse_ema_guidance_payload,
    parse_ema_guidance_search_count,
    validate_ema_guidance_completeness,
)


EMA_SAMPLE_PAYLOAD = {
    "meta": {"total_records": 3, "timestamp": "2026-06-22T06:23:49Z"},
    "data": [
        {
            "title": "Development of new medicinal products for the treatment of smoking - Scientific guideline",
            "summary": "",
            "categories": "Human",
            "first_published_date": "18/12/2008",
            "last_updated_date": "29/05/2026",
            "general_url": "https://www.ema.europa.eu/en/development-new-medicinal-products-treatment-smoking-scientific-guideline",
        },
        {
            "title": "Real-world evidence",
            "summary": "Making greater use of real-world evidence and real-world data can improve decisions.",
            "categories": "Human;Veterinary",
            "first_published_date": "24/07/2024",
            "last_updated_date": "10/06/2026",
            "general_url": "https://www.ema.europa.eu/en/about-us/how-we-work/data-regulation-big-data-other-sources/real-world-evidence",
        },
        {
            "title": "Languages on this website",
            "summary": "Corporate page.",
            "categories": "Corporate",
            "first_published_date": "17/02/2023",
            "last_updated_date": "16/06/2026",
            "general_url": "https://www.ema.europa.eu/en/about-us/about-website/languages-website",
        },
    ],
}


def test_parse_ema_guidance_payload_keeps_all_guidance_information_rows():
    documents = parse_ema_guidance_payload(EMA_SAMPLE_PAYLOAD)

    assert len(documents) == 3
    document = documents[0]
    assert document.title == "Development of new medicinal products for the treatment of smoking"
    assert document.agency == "EMA"
    assert document.jurisdiction == "EU"
    assert document.status_normalized == "final"
    assert document.published_date == date(2008, 12, 18)
    assert document.updated_date == date(2026, 5, 29)
    assert document.summary == "Not available."
    assert document.source_page_url.endswith("smoking-scientific-guideline")
    assert documents[1].title == "Real-world evidence"
    assert documents[2].topic_raw == "Corporate"


def test_ema_crawler_uses_injected_fetcher():
    crawler = EMACrawler(fetch_json=lambda: EMA_SAMPLE_PAYLOAD)

    documents = crawler.crawl()

    assert len(documents) == 3


def test_ema_crawler_does_not_check_search_count_by_default():
    crawler = EMACrawler(fetch_detail_html=lambda url: "")

    assert crawler.fetch_search_count is None


def test_parse_ema_date_prefers_european_day_month_order():
    assert _parse_ema_date("12/03/2026") == date(2026, 3, 12)
    assert _parse_ema_date("08/05/2026") == date(2026, 5, 8)


def test_parse_ema_guidance_payload_does_not_turn_european_dates_into_future_dates():
    payload = {
        "meta": {"total_records": 1},
        "data": [
            {
                "title": "Veterinary antibiotics: Dosage review and adjustment (ADRA) project",
                "summary": "EMA page summary.",
                "categories": "Veterinary",
                "first_published_date": "12/03/2026",
                "last_updated_date": "",
                "general_url": "https://www.ema.europa.eu/en/example",
            }
        ],
    }

    documents = parse_ema_guidance_payload(payload)

    assert documents[0].published_date == date(2026, 3, 12)


def test_parse_ema_guidance_search_count_from_active_facet():
    html = """
    <main>
      <h2><span>Search results</span> (2069)</h2>
      <a class="is-active" data-drupal-facet-item-value="004_ema_guidance_and_info" data-drupal-facet-item-count="2069">
        <span>Guidance and information (2069)</span>
      </a>
    </main>
    """

    assert parse_ema_guidance_search_count(html) == 2069


def test_parse_ema_guidance_search_count_from_heading():
    html = """
    <main>
      <h2><span class="results-count">Search results</span> (2,069)</h2>
    </main>
    """

    assert parse_ema_guidance_search_count(html) == 2069


def test_validate_ema_guidance_completeness_rejects_search_json_mismatch():
    documents = parse_ema_guidance_payload(EMA_SAMPLE_PAYLOAD)
    payload = {**EMA_SAMPLE_PAYLOAD, "meta": {"total_records": 2046}}

    try:
        validate_ema_guidance_completeness(payload, documents, 2069)
    except ValueError as exc:
        assert "search page reports 2069" in str(exc)
        assert "JSON reports 2046" in str(exc)
    else:
        raise AssertionError("Expected EMA completeness mismatch to fail")


def test_ema_crawler_stops_when_search_count_does_not_match_json():
    crawler = EMACrawler(fetch_json=lambda: EMA_SAMPLE_PAYLOAD, fetch_search_count=lambda: 2069)

    assert crawler.crawl() == []


def test_extract_ema_pdf_url_from_html_returns_document_pdf():
    html = """
    <main>
      <a href="/en/documents/scientific-guideline/example-guideline_en.pdf">Download PDF</a>
    </main>
    """

    assert (
        extract_ema_pdf_url_from_html(html)
        == "https://www.ema.europa.eu/en/documents/scientific-guideline/example-guideline_en.pdf"
    )


def test_enrich_ema_documents_with_pdf_links_sets_document_url():
    documents = parse_ema_guidance_payload(EMA_SAMPLE_PAYLOAD)

    enriched = enrich_ema_documents_with_pdf_links(
        documents,
        lambda url: '<a href="/en/documents/scientific-guideline/smoking-guideline_en.pdf">PDF</a>',
    )

    assert enriched[0].document_url == "https://www.ema.europa.eu/en/documents/scientific-guideline/smoking-guideline_en.pdf"
    assert enriched[0].document_format == "PDF"
