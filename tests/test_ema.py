import json
import unittest

from guidance_collector.ema import collect_ema_guidance, parse_ema_general_payload


EMA_SAMPLE_PAYLOAD = {
    "meta": {"total_records": 3, "timestamp": "2026-05-01T06:10:16Z"},
    "data": [
        {
            "title": "ICH Q3C (R9) Residual solvents - Scientific guideline",
            "summary": "This guideline recommends acceptable amounts for residual solvents in medicines.",
            "categories": "Human",
            "first_published_date": "11/02/2011",
            "last_updated_date": "29/04/2026",
            "general_url": "https://www.ema.europa.eu/en/ich-q3c-r9-residual-solvents-scientific-guideline",
        },
        {
            "title": "Submission dates",
            "summary": "The timing and planning of submissions is important.",
            "categories": "Human",
            "first_published_date": "31/12/2009",
            "last_updated_date": "20/04/2026",
            "general_url": "https://www.ema.europa.eu/en/human-regulatory-overview/marketing-authorisation/submission-dates",
        },
        {
            "title": "Demonstration of biosimilarity of biological veterinary medicinal products - Scientific guideline",
            "summary": "",
            "categories": "Veterinary",
            "first_published_date": "24/04/2026",
            "last_updated_date": "",
            "general_url": "https://www.ema.europa.eu/en/demonstration-biosimilarity-biological-veterinary-medicinal-products-scientific-guideline",
        },
    ],
}


class EMAParserTests(unittest.TestCase):
    def test_parse_ema_general_payload_keeps_scientific_guidelines(self):
        records = parse_ema_general_payload(EMA_SAMPLE_PAYLOAD)

        self.assertEqual(len(records), 2)
        first = records[0]
        self.assertEqual(first.health_authority, "EMA")
        self.assertEqual(first.guidance_name, "ICH Q3C (R9) Residual solvents")
        self.assertEqual(first.summary, "This guideline recommends acceptable amounts for residual solvents in medicines.")
        self.assertEqual(first.issue_date, "2011-02-11")
        self.assertEqual(first.fda_organization, "European Medicines Agency")
        self.assertEqual(first.topic, "Human")
        self.assertEqual(first.guidance_status, "Scientific guideline")
        self.assertEqual(first.open_for_comment, "")
        self.assertEqual(first.comment_closing_date_on_draft, "")
        self.assertEqual(first.guidance_page_link, "https://www.ema.europa.eu/en/ich-q3c-r9-residual-solvents-scientific-guideline")

    def test_collect_ema_guidance_uses_fetch_json(self):
        calls = []

        def fake_fetch(url):
            calls.append(url)
            return EMA_SAMPLE_PAYLOAD

        records = collect_ema_guidance(fetch_json=fake_fetch)

        self.assertEqual(len(records), 2)
        self.assertEqual(len(calls), 1)

    def test_sample_payload_is_json_serializable(self):
        self.assertIsInstance(json.loads(json.dumps(EMA_SAMPLE_PAYLOAD)), dict)


if __name__ == "__main__":
    unittest.main()
