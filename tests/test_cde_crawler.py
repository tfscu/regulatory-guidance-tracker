import pytest

from app.crawlers.cde import CDECrawler, parse_cde_guidance_html, parse_cde_guidance_items


def test_parse_cde_guidance_items_filters_to_chemical_and_biologics():
    documents = parse_cde_guidance_items(
        [
            {
                "title": "关于发布化学药品临床试验指导原则的通告",
                "drugType": "化学药",
                "publishDate": "2026-03-25",
                "url": "/main/news/viewInfoCommon/example",
                "fileUrl": "/files/example.pdf",
                "summary": "",
            },
            {
                "title": "关于发布中药指导原则的通告",
                "drugType": "中药",
                "publishDate": "2026-01-01",
                "url": "/main/news/viewInfoCommon/tcm",
            },
        ]
    )

    assert len(documents) == 1
    document = documents[0]
    assert document.title == "关于发布化学药品临床试验指导原则的通告"
    assert document.agency == "CDE"
    assert document.jurisdiction == "China"
    assert document.status_normalized == "final"
    assert document.product_area == "化学药"
    assert document.document_format == "PDF"
    assert document.summary == "Not available."


def test_parse_cde_guidance_html_rejects_protection_page():
    with pytest.raises(ValueError):
        parse_cde_guidance_html('<meta id="9DhefwqGPrzGxEp9hPaoag" content="challenge">')


def test_cde_crawler_returns_empty_on_protection_page():
    crawler = CDECrawler(fetch_text=lambda: '<script>$_ts={}</script>')

    assert crawler.crawl() == []
