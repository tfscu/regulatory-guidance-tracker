# Regulatory Guidance Tracker

Small internal web application for tracking regulatory guidance metadata across FDA, EMA, ICH, CDE/NMPA, and PMDA sources.

The current MVP focuses on a runnable Streamlit dashboard, SQLite persistence, deterministic status/topic tagging, seed/demo data, CSV export, and Markdown update reporting. It keeps the existing `guidance_collector` FDA/EMA utilities intact and adds a new `app/` package for the web product.

## Setup

```powershell
pip install -e ".[test]"
```

## Quick Start

Initialize the SQLite database:

```powershell
python -m app.cli init-db
```

Load seed/demo records so the app is immediately usable:

```powershell
python -m app.cli seed
```

Run the MVP crawler pipeline. FDA uses a real metadata endpoint; EMA, ICH, CDE, and PMDA are placeholders in this first version and get seed/demo records when empty.

```powershell
python -m app.cli crawl --agency all
```

Launch the web app:

```powershell
streamlit run app/web/streamlit_app.py
```

On a fresh checkout or hosted Streamlit deployment, the app automatically copies
`data_snapshots/regulatory_guidance_snapshot.db` to `data/regulatory_guidance.db`
when the runtime database does not exist.

Or print the launch instruction:

```powershell
python -m app.cli run-web
```

## Export and Report

Export the SQLite records to CSV:

```powershell
python -m app.cli export-csv
```

Generate a deterministic Markdown update report:

```powershell
python -m app.cli generate-report
```

Outputs are written under `data/exports/`.

## Web Deployment

Use GitHub as the code repository and Streamlit Community Cloud as the hosted
web runtime.

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create a new app from the GitHub repository.
3. Set the main file path to:

```text
app/web/streamlit_app.py
```

The committed snapshot at `data_snapshots/regulatory_guidance_snapshot.db`
provides initial public data for the web app. Do not commit the runtime `data/`
directory; it contains local SQLite files, exports, logs, and temporary files.

## Data Model

The MVP stores `GuidanceDocument` records in `data/regulatory_guidance.db` with fields for agency, jurisdiction, title, source/document URLs, publication/update/comment dates, raw and normalized status, topic tags, summary, language, reference number, first/last seen timestamps, change type, and manual-review flag.

Allowed normalized statuses:

- `draft`
- `final`
- `open_for_comment`
- `implemented`
- `withdrawn`
- `superseded`
- `unknown`

Allowed change types:

- `new`
- `updated`
- `unchanged`
- `removed`
- `unknown`

## Crawlers

- `FDA`: implemented as the first real MVP crawler, reusing the official FDA guidance DataTables endpoint from the existing collector.
- `EMA`, `ICH`, `CDE`, `PMDA`: clean placeholders that return no records and log that the crawler is not yet implemented.
- `seed`: provides clearly marked seed/demo records covering all agencies and priority topics so the dashboard can be demonstrated without live crawling.

To add a new agency crawler:

1. Create a class in `app/crawlers/` that implements `BaseCrawler.crawl()`.
2. Return `GuidanceDocument` objects.
3. Normalize status and topic with `app.normalizers.status` and `app.normalizers.topics`.
4. Register it in `app/crawlers/__init__.py`.
5. Add focused tests for parsing and normalization behavior.

## Tests

Run the existing collector tests:

```powershell
python -m unittest discover -s tests -v
```

Run the MVP pytest suite:

```powershell
python -m pytest -q
```

## Known Limitations

- First version does not fully crawl every official website.
- Placeholder crawlers are intentionally non-fatal.
- No PDF downloading, PDF parsing, authentication, Docker, or LLM API calls.
- Source websites may change structure or block automated requests; seed/demo records keep the app runnable when live crawling fails.

## Future Roadmap

- Replace placeholder crawlers one agency at a time.
- Add richer source-specific parsing for EMA open consultations, CDE listings, PMDA regulatory pages, and ICH consultations.
- Add optional PDF metadata extraction behind a separate interface.
- Add authentication only if the app is deployed beyond a trusted internal environment.

## Legacy FDA Collection

The original CSV/static-report collector is still available. Run a capped FDA smoke test:

```powershell
python -m guidance_collector.fda --max-records 20 --output exports/fda_guidance.csv
```

Run the full FDA export:

```powershell
python -m guidance_collector.fda --output exports/fda_guidance.csv
```

By default, the legacy FDA collector enriches the `Summary` column from each FDA guidance detail page. Use `--skip-detail-summaries` for a faster table-only export.

If FDA blocks direct scripted access with a timeout, closed connection, `503`, or non-JSON response, use the official browser table instead:

1. Open https://www.fda.gov/regulatory-information/search-fda-guidance-documents in Chrome or Edge.
2. In the table's "Show entries" control, choose `All`.
3. Open Developer Tools, then the Console tab.
4. Paste the contents of `tools/fda_browser_export.js` and press Enter.
5. Wait for the console message that all detail-page summaries have been collected. For the full FDA table this can take several minutes.
6. Move the downloaded `fda_guidance.csv` to `exports/fda_guidance.csv`.
7. Regenerate the report:

```powershell
python -m guidance_collector.report --input exports/fda_guidance.csv --output reports/fda_guidance.html
```

Export JSON instead:

```powershell
python -m guidance_collector.fda --format json --output exports/fda_guidance.json
```

Render the CSV as an HTML report:

```powershell
python -m guidance_collector.report --input exports/fda_guidance.csv --output reports/fda_guidance.html
```

## EMA Collection

Run the EMA scientific-guideline export:

```powershell
python -m guidance_collector.ema --output exports/ema_guidance.csv
```

EMA's source is the official JSON data file documented by EMA for automated systems:

```text
https://www.ema.europa.eu/en/documents/report/general-json-report_en.json
```

## Combined FDA + EMA Report

Render both authorities together:

```powershell
python -m guidance_collector.report --input exports/fda_guidance.csv --input exports/ema_guidance.csv --output reports/guidance_dashboard.html
```

## Export Columns

- Health Authority
- Guidance Name
- Summary
- Issue Date
- FDA Organization
- Topic
- Guidance Status
- Open for Comment
- Comment Closing Date on Draft
- Guidance PDF Link
- Guidance Page Link
- Docket Number

## Notes

The FDA page exposes its table via `https://www.fda.gov/datatables-json/search-for-guidance.json`. Some networks may block direct command-line access to FDA; if that happens, retry from a network/browser environment that can access FDA.gov.
