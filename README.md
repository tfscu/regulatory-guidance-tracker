# Regulatory Guidance Tracker

A local Streamlit web app for browsing regulatory guidance records from FDA, EMA, ICH, CDE, and PMDA.

The app uses SQLite for storage and ships with a public database snapshot, so a new user can clone or download this repository and run the dashboard locally without crawling websites first.

## What You Get

- Streamlit dashboard with agency, status, topic, keyword, title, and date filters
- Multi-row selection with CSV export for selected guidance records
- Compact per-agency crawl timestamps and direct source/PDF links
- SQLite database model for guidance metadata
- Current public database snapshot at `data_snapshots/regulatory_guidance_snapshot.db`
- Optional crawler/update workflow for FDA, EMA, ICH, CDE, and PMDA
- CSV and Markdown exports under `data/exports/`

Current snapshot contents:

| Agency | Records |
| --- | ---: |
| FDA | 2791 |
| EMA | 2047 |
| CDE | 552 |
| ICH | 44 |
| PMDA | 14 |
| Total | 5448 |

## Requirements

- Python 3.11 or newer
- Git, if cloning instead of downloading a ZIP
- PowerShell, if using the provided update script

## Quick Start: Use the Included Database

This is the easiest path. It uses the database snapshot already included in this repository.

```powershell
git clone https://github.com/tfscu/regulatory-guidance-tracker.git
cd regulatory-guidance-tracker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app/web/streamlit_app.py
```

Open the local URL printed by Streamlit, usually:

```text
http://localhost:8501
```

On first launch, if `data/regulatory_guidance.db` does not exist, the app automatically copies:

```text
data_snapshots/regulatory_guidance_snapshot.db
```

to:

```text
data/regulatory_guidance.db
```

The `data/` directory is local runtime data. It is intentionally not committed to Git.

## If You Download a ZIP Instead of Cloning

1. Download and unzip the repository.
2. Open a terminal in the unzipped folder.
3. Run the same setup commands starting from `python -m venv .venv`.

The included snapshot works the same way.

## Refresh the Database Yourself

Use this path if you want to crawl the official websites again and update the local SQLite database.

First install the project and Playwright browser dependency:

```powershell
python -m pip install -e .
python -m playwright install chromium
```

Then run the update script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update_guidance_database.ps1
```

The script will:

- back up the current SQLite database to `data/backups/`
- crawl all supported agencies
- upsert records into `data/regulatory_guidance.db`
- export `data/exports/regulatory_guidance.csv`
- generate `data/exports/regulatory_update_report.md`
- write a run log under `data/logs/`

To update only one agency:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update_guidance_database.ps1 -Agency EMA
```

Supported values are:

```text
all, FDA, EMA, ICH, CDE, PMDA
```

To preview the steps without changing files:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update_guidance_database.ps1 -DryRun
```

## Update Strategy

The crawler does not only look for new records. It fetches the full official list for each supported agency and upserts into SQLite:

- new records become `new`
- changed records become `updated`
- unchanged records become `unchanged`
- `first_seen_at` is preserved
- `last_seen_at` is refreshed

The app shows a `Data refresh status` table so users can see when each agency was last crawled or imported.

## Data Sources

- FDA: official FDA guidance table endpoint and guidance pages
- EMA: official JSON data file documented by EMA
- ICH: official ICH API used by the ICH website
- CDE: official CDE guidance database filters for chemical drugs and biological products
- PMDA: official English clinical-trial and vaccine regulatory-information pages

EMA source used by this project:

```text
https://www.ema.europa.eu/en/documents/report/general-json-report_en.json
```

## Common Commands

Initialize an empty SQLite schema:

```powershell
python -m app.cli init-db
```

Run crawler manually:

```powershell
python -m app.cli crawl --agency all --all-records --no-seed-if-empty
```

Export CSV:

```powershell
python -m app.cli export-csv
```

Generate Markdown report:

```powershell
python -m app.cli generate-report
```

Print web launch command:

```powershell
python -m app.cli run-web
```

## Troubleshooting

If the dashboard has no records, delete the local runtime database and restart the app:

```powershell
Remove-Item data\regulatory_guidance.db
streamlit run app/web/streamlit_app.py
```

The app will copy the included snapshot again.

If crawling fails, check:

- your internet connection
- whether the source website is temporarily blocking automated requests
- the log file under `data/logs/`
- the database backup under `data/backups/`

FDA detail pages may return `401 Unauthorized` for some summary enrichment requests. The FDA list records can still be imported from the table endpoint.

## Tests

Install test dependencies:

```powershell
python -m pip install -e ".[test]"
```

Run pytest:

```powershell
python -m pytest tests -q --basetemp data\pytest_tmp_readme -p no:cacheprovider
```

Run the legacy unittest baseline:

```powershell
python -m unittest discover -s tests -v
```

## Streamlit Community Cloud

This repository can also be deployed on Streamlit Community Cloud.

Use:

```text
Main file path: app/web/streamlit_app.py
```

The hosted app uses `data_snapshots/regulatory_guidance_snapshot.db` as its initial database. To update hosted data, refresh the local database, update the snapshot, commit, and push to GitHub.

## Repository Layout

```text
app/                         Streamlit app, CLI, crawlers, storage, reports
configs/                     Source configuration
data_snapshots/              Committed SQLite snapshot for local/hosted startup
guidance_collector/          Legacy FDA/EMA collector utilities
scripts/                     Portable database update script
tests/                       Pytest and unittest coverage
```

## Notes

- The committed snapshot contains public regulatory guidance metadata only.
- The runtime `data/` directory can contain local databases, backups, exports, and logs. Keep it local.
- PMDA coverage currently includes the official English Clinical Trials page and the Clinical Studies, Prototype Vaccines, and SARS-CoV-2 evaluation sections of the Vaccines and Blood Products page.
