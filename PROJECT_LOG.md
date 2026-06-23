# Project Log

## 2026-06-22 - MVP native Streamlit table milestone

Status: checkpoint candidate

Summary:
- Regulatory Guidance Tracker MVP is runnable with Streamlit, SQLite, CLI, FDA crawler, deterministic normalizers, CSV export, Markdown report, and tests.
- The web app is currently on the native Streamlit `st.dataframe(on_select="rerun", selection_mode="multi-row")` version after reverting the custom HTML/component table experiment.
- This milestone keeps the existing `guidance_collector` package intact and preserves the current MVP architecture under `app/`.

Validation:
- `python -c "import app.web.streamlit_app; print('import ok')"` passed.
- `python -m pytest -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 33 tests.

Rollback point recommendation:
- Branch: `codex/mvp-baseline-native-streamlit-table`
- Tag: `mvp-native-streamlit-table-2026-06-22`
- Commit message: `chore: checkpoint native streamlit guidance tracker milestone`

Notes:
- Repository had no prior commits when this milestone was recorded.
- `data/` runtime artifacts should not be committed unless explicitly approved.
- Future milestones should update this file after validation.

## 2026-06-22 - ICH, EMA, and CDE crawler milestone

Status: implemented

Summary:
- Added app-level ICH crawler using the official ICH efficacy guidelines API.
- Added app-level EMA crawler using EMA's official guidance and information JSON data file with `?download=1`.
- Added app-level CDE crawler scaffold with official CDE guidance page fetching, protection-page detection, and reusable parsers for CDE HTML/item payloads.
- Replaced placeholder registry entries for ICH, EMA, and CDE.
- Corrected CDE Chinese status normalization rules and added crawler-specific tests.

Validation:
- `python -m pytest -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 40 tests.
- `python -m unittest discover -s tests -v` passed with 19 unittest tests.
- Live crawler smoke check: ICH returned 44 records; EMA returned 1101 records; CDE returned 0 records because the official site returned a protection page.
- CLI crawl saved 44 ICH records and 1101 EMA records to SQLite with `--no-seed-if-empty`; CDE saved 0 records and did not seed demo data.

Notes:
- CDE live HTML requests currently return a protection page in automated HTTP/headless checks, so the crawler avoids saving false records and returns an empty list with a warning until a stable official data endpoint or browser-export payload is available.

## 2026-06-23 - CDE browser-AJAX crawler milestone

Status: implemented

Summary:
- Reworked the CDE crawler to use Playwright with local Microsoft Edge so the official CDE page can complete its JavaScript protection flow.
- Captured and reused the official `/zdyz/getDomesticGuideList` AJAX endpoint from inside the rendered page.
- Crawls CDE records for `zyfl1=化学药` and `zyfl1=生物制品` with `zyfl2` empty, matching the requested scope: chemical drugs and biological products, all professional categories.
- Deduplicates overlapping chemical/biologic records by `zdyzIdCODE`.
- Maps compact CDE dates like `20260601`, CDE `颁布` status, source detail URLs, and `Not available.` summaries/document links where detail enrichment is not yet available.
- Added `playwright` as a runtime dependency because CDE requires browser execution.

Validation:
- Targeted tests: `python -m pytest tests\test_cde_crawler.py tests\test_status_normalizer.py tests\test_date_parser.py -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 12 tests.
- Live CDE crawler smoke check returned 494 unique CDE records.
- CLI crawl: `python -m app.cli crawl --agency CDE --no-seed-if-empty` saved 494 CDE records.
- SQLite agency counts after crawl: FDA 2788, EMA 1101, ICH 44, CDE 494; total 4427.

Notes:
- CDE detail pages expose attachment links, but the list API does not include attachment `idCODE`; document URL enrichment should be a separate milestone to avoid making this successful list crawl slow and brittle.

## 2026-06-23 - CDE attachment-link enrichment milestone

Status: implemented

Summary:
- Added CDE detail-page enrichment after the protected browser/AJAX list crawl succeeds.
- Uses the same Playwright browser context to request each official CDE detail page and extract the first `/zdyz/downloadAtt` attachment link.
- Stores detected attachment URLs in `document_url` and classifies obvious PDF/DOC/DOCX attachment formats in `document_format`.
- Keeps CDE records without detected attachments as `Not available.` in the web detail view/export behavior.

Validation:
- Targeted tests: `python -m pytest tests\test_cde_crawler.py -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 5 tests.
- Live CDE crawler smoke check returned 494 CDE records, 490 records with `document_url`, and 403 records classified as PDF.
- CLI crawl: `python -m app.cli crawl --agency CDE --no-seed-if-empty` saved 494 CDE records.
- SQLite agency counts after crawl: FDA 2788, EMA 1101, ICH 44, CDE 494; total 4427.

Notes:
- CDE detail-page enrichment is slower than list-only crawling because it visits hundreds of detail pages.
- Four CDE records did not expose a detected attachment link during the live smoke check and should remain `Not available.` unless the official page later changes.

## 2026-06-23 - CDE complete-list parser fix milestone

Status: implemented

Summary:
- Fixed CDE parser logic that incorrectly dropped official CDE guidance records when the title did not contain the literal phrase `指导原则`.
- Kept the requested CDE scope boundary: chemical drugs and biological products from the official CDE guidance list.
- Confirmed the previously missing record `化学仿制药生物等效性研究重大缺陷情形` is now captured with source page and PDF attachment URL.

Validation:
- Targeted tests: `python -m pytest tests\test_cde_crawler.py -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 6 tests.
- Live CDE crawler smoke check returned 552 CDE records and included `zdyzIdCODE=6b02391b10ae8dab7868d00cadd3cce4`.
- CLI crawl: `python -m app.cli crawl --agency CDE --no-seed-if-empty` saved 552 CDE records.
- SQLite verification found 552 CDE records and 1 target hit for `化学仿制药生物等效性研究重大缺陷情形`.
- Full validation passed: `python -m pytest -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 43 tests; `python -m unittest discover -s tests -v` passed with 19 tests.

Notes:
- The CDE official list endpoint itself returned 552 unique records before parsing; the earlier 494 count was caused by local parser filtering, not by missing browser/API access.
