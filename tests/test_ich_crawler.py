from datetime import date

from app.crawlers.ich import EFFICACY_PAGE_URL, ICHCrawler, parse_ich_efficacy_payload


ICH_SAMPLE_PAYLOAD = {
    "items": [
        {
            "bundleInfo": {"updated": "2025-08-12T15:00:36+0200"},
            "mainWidgets": {
                "items": [
                    {
                        "accordions": {
                            "items": [
                                {
                                    "items": [
                                        {
                                            "code": "E20",
                                            "title": "Adaptive Designs for Clinical Trials",
                                            "description": "<p>Draft adaptive clinical trial guidance.</p>",
                                            "status": "Step 3",
                                            "details": {
                                                "stepDate": "25 June 2025",
                                                "infoTitle": "Public consultation dates",
                                                "info": [{"text": "Deadline for comments by 1 December 2099"}],
                                            },
                                            "fileGroups": [
                                                {
                                                    "title": "Guideline",
                                                    "weight": 0,
                                                    "files": [
                                                        {
                                                            "uri": "https://database.ich.org/E20.docx",
                                                            "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                                        }
                                                    ],
                                                }
                                            ],
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            },
        }
    ]
}


def test_parse_ich_efficacy_payload_extracts_guidelines():
    documents = parse_ich_efficacy_payload(ICH_SAMPLE_PAYLOAD)

    assert len(documents) == 1
    document = documents[0]
    assert document.title == "ICH E20 - Adaptive Designs for Clinical Trials"
    assert document.agency == "ICH"
    assert document.jurisdiction == "International"
    assert document.source_page_url == EFFICACY_PAGE_URL
    assert document.document_url == "https://database.ich.org/E20.docx"
    assert document.document_format == "DOCX"
    assert document.published_date == date(2025, 6, 25)
    assert document.updated_date == date(2025, 8, 12)
    assert document.comment_end_date == date(2099, 12, 1)
    assert document.status_normalized == "open_for_comment"
    assert document.topic_normalized == "adaptive_design"
    assert document.product_area == "Efficacy"
    assert document.summary == "Draft adaptive clinical trial guidance."
    assert document.reference_number == "E20"


def test_ich_crawler_uses_injected_fetcher():
    crawler = ICHCrawler(fetch_json=lambda: ICH_SAMPLE_PAYLOAD)

    documents = crawler.crawl()

    assert [document.reference_number for document in documents] == ["E20"]
