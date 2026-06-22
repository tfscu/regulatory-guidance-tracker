# Guidance Collector Findings

## FDA Official Source

- Official page: https://www.fda.gov/regulatory-information/search-fda-guidance-documents
- The FDA page states that the guidance table can be searched/filtered by product, date issued, FDA organizational unit, document type, subject/topic, draft/final status, and comment period dates.
- The page content was current as of 2026-05-22 in the rendered official page.
- The rendered table headers include: Summary, Document, Issue Date, FDA Organization, Topic, Guidance Status, Open for Comment, Comment Closing Date on Draft, Docket Number.

## FDA Data Endpoint

- Browser inspection found Drupal DataTables settings for view `fda_guidance_documents`, display `block_11`.
- The view base path is `datatables-json/search-for-guidance.json`.
- The table is paginated in the browser; the DOM initially shows only 10 rows, so the collector must use pagination rather than the visible HTML alone.
- Direct command-line requests to the FDA page returned either "Not found" or a TLS handshake error in this sandbox. The collector should use standard HTTP first but document that local networks may require browser-like headers or retry.
- A direct Python request to the DataTables endpoint reached FDA after sandbox escalation but FDA returned HTTP 503 Service Unavailable.
- The browser-rendered table showed `Showing 1 to 10 of 2,787 entries`; switching the table length to "All" rendered 2,787 rows.
- Browser-exported row text had character corruption for punctuation/symbols in this environment, so browser DOM export is not suitable as the primary data artifact.

## Representative Row Details

- PDF links are in the Document column as `/media/.../download`.
- Summary/name links are in the Summary column as `/regulatory-information/search-fda-guidance-documents/...`.
- Docket links may point to regulations.gov.
- Comment Closing Date on Draft can be hidden in the rendered table and may be blank.

## EMA Official Source

- Official JSON data page: https://www.ema.europa.eu/en/about-us/about-website/download-website-data-json-data-format
- EMA states the JSON data files are intended for automated access and are updated twice a day.
- The Guidance and information JSON file is `https://www.ema.europa.eu/en/documents/report/general-json-report_en.json`.
- The feed includes page title, summary, categories, first published date, last updated date, and page URL.
- For this first EMA implementation, rows are filtered to EMA scientific guideline pages based on title or URL.
