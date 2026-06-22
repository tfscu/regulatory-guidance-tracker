import csv
import http.client
import json
import unittest
from io import StringIO
from unittest.mock import patch
from urllib.error import HTTPError

from guidance_collector.fda import (
    FDA_DATATABLE_URL,
    FDAFetchError,
    collect_fda_guidance,
    collect_fda_static_guidance,
    enrich_with_detail_summaries,
    extract_guidance_summary_from_html,
    fetch_json_url,
    parse_fda_datatables_payload,
    parse_fda_static_payload,
)
from guidance_collector.schema import EXPORT_COLUMNS, write_csv


FDA_SAMPLE_PAYLOAD = {
    "draw": 1,
    "recordsTotal": 2,
    "recordsFiltered": 2,
    "data": [
        [
            '<a href="/regulatory-information/search-fda-guidance-documents/example-guidance">Example Guidance</a>',
            '<a href="/media/123456/download">PDF (123 KB)<span class="sr-only">PDF of Example Guidance</span></a>',
            "05/20/2026",
            "Center for Drug Evaluation and Research",
            "Biostatistics",
            "Draft",
            "  Yes ",
            "07/20/2026",
            '<a href="https://www.regulations.gov/docket/FDA-2026-D-0001">FDA-2026-D-0001</a>',
        ],
        {
            "field_summary": '<a href="/regulatory-information/search-fda-guidance-documents/final-guidance">Final Guidance</a>',
            "field_document": '<a href="/media/789/download">PDF (222 KB)</a>',
            "field_issue_date": "05/01/2026",
            "field_organization": "Center for Biologics Evaluation and Research",
            "field_topic": "Clinical Trials",
            "field_guidance_status": "Final",
            "field_open_for_comment": "No",
            "field_comment_closing_date": "",
            "field_docket_number": "",
        },
    ],
}


FDA_DETAIL_HTML = """
<html>
  <main class="article main-content">
    <p>Not for implementation. Contains non-binding recommendations.</p>
    <div class="col-md-8">
      <p>
        The purpose of this guidance is to describe the benefit-risk assessment
        framework that the Agency uses in evaluating whether applications meet
        the standard for approval.
      </p>
    </div>
  </main>
</html>
"""

FDA_DETAIL_WITH_GOV_BOILERPLATE_HTML = """
<html>
  <body>
    <p>The .gov means it’s official. Federal government websites often end in .gov or .mil.</p>
    <article class="main-content" id="main-content">
      <div role="main">
        <p>GUIDANCE DOCUMENT</p>
        <p>Not for implementation. Contains non-binding recommendations.</p>
        <p>Search for FDA Guidance Documents</p>
        <p>
          The Food and Drug Administration is announcing the availability of a draft
          guidance for industry. This draft guidance is intended to describe the
          Agency's recommendations for clinical development planning and regulatory
          submission content.
        </p>
      </div>
    </article>
  </body>
</html>
"""

FDA_STATIC_SAMPLE_PAYLOAD = [
    {
        "title": '<a href="/regulatory-information/search-fda-guidance-documents/static-guidance">Static Guidance</a>',
        "field_associated_media_2": '<a href="/media/555/download">Download PDF</a>',
        "field_issue_datetime": "06/01/2026",
        "field_issuing_office_taxonomy": "Center for Drug Evaluation and Research",
        "topics-product": "Biostatistics",
        "field_final_guidance_1": "Final",
        "open-comment": "No",
        "field_comment_close_date": "",
        "field_docket_number": '<a href="https://www.regulations.gov/docket/FDA-2026-D-5555">FDA-2026-D-5555</a>',
    }
]


class FDAParserTests(unittest.TestCase):
    def test_parse_datatables_payload_normalizes_rows(self):
        records = parse_fda_datatables_payload(FDA_SAMPLE_PAYLOAD)

        self.assertEqual(len(records), 2)
        first = records[0]
        self.assertEqual(first.health_authority, "FDA")
        self.assertEqual(first.guidance_name, "Example Guidance")
        self.assertEqual(first.summary, "Example Guidance")
        self.assertEqual(first.issue_date, "2026-05-20")
        self.assertEqual(first.fda_organization, "Center for Drug Evaluation and Research")
        self.assertEqual(first.topic, "Biostatistics")
        self.assertEqual(first.guidance_status, "Draft")
        self.assertEqual(first.open_for_comment, "Yes")
        self.assertEqual(first.comment_closing_date_on_draft, "2026-07-20")
        self.assertEqual(first.guidance_pdf_link, "https://www.fda.gov/media/123456/download")
        self.assertEqual(
            first.guidance_page_link,
            "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/example-guidance",
        )
        self.assertEqual(first.docket_number, "FDA-2026-D-0001")

    def test_parse_static_payload_normalizes_current_fda_json_shape(self):
        records = parse_fda_static_payload(FDA_STATIC_SAMPLE_PAYLOAD)

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.guidance_name, "Static Guidance")
        self.assertEqual(record.issue_date, "2026-06-01")
        self.assertEqual(record.fda_organization, "Center for Drug Evaluation and Research")
        self.assertEqual(record.topic, "Biostatistics")
        self.assertEqual(record.guidance_status, "Final")
        self.assertEqual(record.open_for_comment, "No")
        self.assertEqual(record.guidance_pdf_link, "https://www.fda.gov/media/555/download")
        self.assertEqual(
            record.guidance_page_link,
            "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/static-guidance",
        )
        self.assertEqual(record.docket_number, "FDA-2026-D-5555")

    def test_write_csv_uses_requested_columns(self):
        records = parse_fda_datatables_payload(FDA_SAMPLE_PAYLOAD)
        output = StringIO()

        write_csv(records, output)

        output.seek(0)
        rows = list(csv.DictReader(output))
        self.assertEqual(csv.DictReader(StringIO(output.getvalue())).fieldnames, EXPORT_COLUMNS)
        self.assertEqual(rows[0]["Guidance Name"], "Example Guidance")
        self.assertEqual(rows[0]["Open for Comment"], "Yes")

    def test_collect_fda_guidance_pages_until_total_records_reached(self):
        calls = []

        def fake_fetch(url, params):
            calls.append((url, dict(params)))
            start = params["start"]
            if start == 0:
                return {
                    "draw": 1,
                    "recordsTotal": 3,
                    "recordsFiltered": 3,
                    "data": FDA_SAMPLE_PAYLOAD["data"][:2],
                }
            return {
                "draw": 2,
                "recordsTotal": 3,
                "recordsFiltered": 3,
                "data": [FDA_SAMPLE_PAYLOAD["data"][0]],
            }

        records = collect_fda_guidance(fetch_json=fake_fetch, page_size=2, include_detail_summaries=False)

        self.assertEqual(len(records), 3)
        self.assertEqual(calls[0], (FDA_DATATABLE_URL, {"draw": 1, "start": 0, "length": 2}))
        self.assertEqual(calls[1], (FDA_DATATABLE_URL, {"draw": 2, "start": 2, "length": 2}))

    def test_collect_fda_static_guidance_uses_static_json_payload(self):
        calls = []

        def fake_fetch(url):
            calls.append(url)
            return FDA_STATIC_SAMPLE_PAYLOAD

        records = collect_fda_static_guidance(fetch_json=fake_fetch)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].guidance_name, "Static Guidance")
        self.assertEqual(len(calls), 1)

    def test_extract_guidance_summary_from_detail_page(self):
        summary = extract_guidance_summary_from_html(FDA_DETAIL_HTML)

        self.assertEqual(
            summary,
            "The purpose of this guidance is to describe the benefit-risk assessment "
            "framework that the Agency uses in evaluating whether applications meet "
            "the standard for approval.",
        )

    def test_extract_guidance_summary_skips_fda_page_boilerplate(self):
        summary = extract_guidance_summary_from_html(FDA_DETAIL_WITH_GOV_BOILERPLATE_HTML)

        self.assertTrue(summary.startswith("The Food and Drug Administration is announcing"))
        self.assertNotIn(".gov means", summary)

    def test_enrich_with_detail_summaries_replaces_title_summary(self):
        records = parse_fda_datatables_payload(FDA_SAMPLE_PAYLOAD)
        fetched = []

        def fake_fetch_text(url):
            fetched.append(url)
            return FDA_DETAIL_HTML

        enriched = enrich_with_detail_summaries(records, fetch_text=fake_fetch_text)

        self.assertEqual(len(fetched), 2)
        self.assertEqual(enriched[0].summary, "The purpose of this guidance is to describe the benefit-risk assessment framework that the Agency uses in evaluating whether applications meet the standard for approval.")


class FDAPayloadContractTests(unittest.TestCase):
    def test_sample_payload_is_json_serializable(self):
        self.assertIsInstance(json.loads(json.dumps(FDA_SAMPLE_PAYLOAD)), dict)


class FDAFetchTests(unittest.TestCase):
    def test_fetch_json_url_wraps_http_errors_with_endpoint_context(self):
        error = HTTPError(
            url=FDA_DATATABLE_URL,
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=None,
        )
        with patch("guidance_collector.fda.request.urlopen", side_effect=error):
            with self.assertRaises(FDAFetchError) as raised:
                fetch_json_url(FDA_DATATABLE_URL, {"draw": 1, "start": 0, "length": 1})

        self.assertIn("503", str(raised.exception))
        self.assertIn("search-for-guidance.json", str(raised.exception))
        error.close()

    def test_fetch_json_url_wraps_non_json_responses(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b"Not found"

        with patch("guidance_collector.fda.request.urlopen", return_value=FakeResponse()):
            with self.assertRaises(FDAFetchError) as raised:
                fetch_json_url(FDA_DATATABLE_URL, {"draw": 1, "start": 0, "length": 1})

        self.assertIn("non-JSON", str(raised.exception))

    def test_fetch_json_url_wraps_remote_disconnects(self):
        error = http.client.RemoteDisconnected("Remote end closed connection without response")
        with patch("guidance_collector.fda.request.urlopen", side_effect=error):
            with self.assertRaises(FDAFetchError) as raised:
                fetch_json_url(FDA_DATATABLE_URL, {"draw": 1, "start": 0, "length": 1})

        self.assertIn("closed the connection", str(raised.exception))

    def test_fetch_json_url_wraps_timeouts(self):
        with patch("guidance_collector.fda.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(FDAFetchError) as raised:
                fetch_json_url(FDA_DATATABLE_URL, {"draw": 1, "start": 0, "length": 1})

        self.assertIn("timed out", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
