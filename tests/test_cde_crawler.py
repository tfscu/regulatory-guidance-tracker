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


def test_parse_cde_guidance_items_maps_live_api_shape():
    documents = parse_cde_guidance_items(
        [
            {
                "issueDate": "20260601",
                "nowstate": "颁布",
                "fclass": "化学药,生物制品",
                "title": "关于开发适宜药品包装规格的指导原则",
                "zdyzIdCODE": "981efd549bda05ee430ec550583776fc",
            }
        ]
    )

    assert len(documents) == 1
    document = documents[0]
    assert document.published_date.isoformat() == "2026-06-01"
    assert document.source_page_url.endswith("zdyzIdCODE=981efd549bda05ee430ec550583776fc")
    assert document.document_url is None
    assert document.status_raw == "颁布"
    assert document.status_normalized == "final"
    assert document.reference_number == "981efd549bda05ee430ec550583776fc"


def test_parse_cde_guidance_html_rejects_protection_page():
    with pytest.raises(ValueError):
        parse_cde_guidance_html('<meta id="9DhefwqGPrzGxEp9hPaoag" content="challenge">')


def test_cde_crawler_uses_injected_items_before_html_fallback():
    crawler = CDECrawler(
        fetch_text=lambda: '<script>$_ts={}</script>',
        fetch_items=lambda: [
            {
                "issueDate": "20260601",
                "nowstate": "颁布",
                "fclass": "生物制品",
                "title": "预防用mRNA疫苗临床试验技术指导原则（试行）",
                "zdyzIdCODE": "9c92f5cfa79fc44da0ac28d2b3a0f6b3",
            }
        ],
    )

    documents = crawler.crawl()

    assert len(documents) == 1
    assert documents[0].product_area == "生物制品"
