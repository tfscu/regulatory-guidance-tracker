import tempfile
import unittest
from pathlib import Path

from guidance_collector.report import render_html_report, write_html_report


SAMPLE_RECORD = {
    "Health Authority": "FDA",
    "Guidance Name": "Example Draft Guidance",
    "Summary": "Example Draft Guidance",
    "Issue Date": "2026-05-20",
    "FDA Organization": "Center for Drug Evaluation and Research",
    "Topic": "Biostatistics",
    "Guidance Status": "Draft",
    "Open for Comment": "Yes",
    "Comment Closing Date on Draft": "2026-07-20",
    "Guidance PDF Link": "https://www.fda.gov/media/123456/download",
}

EMA_SAMPLE_RECORD = {
    "Health Authority": "EMA",
    "Guidance Name": "ICH Q3C (R9) Residual solvents",
    "Summary": "EMA scientific guideline summary",
    "Issue Date": "2011-02-11",
    "FDA Organization": "European Medicines Agency",
    "Topic": "Human",
    "Guidance Status": "Scientific guideline",
    "Open for Comment": "",
    "Comment Closing Date on Draft": "",
    "Guidance PDF Link": "",
}


class HtmlReportTests(unittest.TestCase):
    def test_render_html_report_contains_metrics_filters_and_record_payload(self):
        html = render_html_report([SAMPLE_RECORD, EMA_SAMPLE_RECORD], source_status="FDA status message")

        self.assertIn("Guidance Intelligence Dashboard", html)
        self.assertIn('id="metric-records"', html)
        self.assertIn('id="metric-authorities"', html)
        self.assertIn('id="search"', html)
        self.assertIn('id="authority"', html)
        self.assertIn('id="organization"', html)
        self.assertIn("Organization / Committee", html)
        self.assertIn("Example Draft Guidance", html)
        self.assertIn("ICH Q3C (R9) Residual solvents", html)
        self.assertIn("FDA status message", html)
        self.assertIn("https://www.fda.gov/media/123456/download", html)

    def test_write_html_report_combines_multiple_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            fda_csv = Path(tmp) / "fda.csv"
            ema_csv = Path(tmp) / "ema.csv"
            output = Path(tmp) / "report.html"
            header = ",".join(SAMPLE_RECORD.keys())
            fda_csv.write_text(header + "\n" + ",".join(SAMPLE_RECORD.values()) + "\n", encoding="utf-8")
            ema_csv.write_text(header + "\n" + ",".join(EMA_SAMPLE_RECORD.values()) + "\n", encoding="utf-8")

            count = write_html_report([fda_csv, ema_csv], output)

            self.assertEqual(count, 2)
            text = output.read_text(encoding="utf-8")
            self.assertIn("Example Draft Guidance", text)
            self.assertIn("ICH Q3C", text)

    def test_write_html_report_handles_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.html"

            count = write_html_report(Path(tmp) / "missing.csv", output)

            self.assertEqual(count, 0)
            text = output.read_text(encoding="utf-8")
            self.assertIn("Input file not found", text)
            self.assertIn("No guidance records loaded.", text)


if __name__ == "__main__":
    unittest.main()
