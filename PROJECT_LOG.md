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

## 2026-06-23 - EMA JSON refresh and PDF-link enrichment milestone

Status: implemented

Summary:
- Updated the app-level EMA crawler to use the official `general-json-report_en.json` URL as the primary source, with the previous `?download=1` variant as fallback.
- Added EMA detail-page enrichment to extract official PDF links from each guidance page into `document_url`.
- Added bounded concurrent PDF enrichment so the 1101 EMA guidance detail pages can be processed in a practical time.
- Added a repository/CLI agency-clearing path so old EMA records can be removed before importing refreshed EMA data.

Validation:
- Live EMA JSON fetch returned 2046 raw rows and parsed 1101 EMA guidance records.
- Live EMA PDF enrichment returned 1101 EMA guidance records, with 1006 PDF links in the smoke check.
- CLI refresh: `python -m app.cli clear-agency EMA; python -m app.cli crawl --agency EMA --no-seed-if-empty` deleted 1101 old EMA records and saved 1101 refreshed EMA records.
- SQLite verification after CLI refresh found 1101 EMA records and 1016 EMA records with `document_url`.
- Full validation passed: `python -m pytest -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 46 tests; `python -m unittest discover -s tests -v` passed with 19 tests.

Notes:
- Some EMA detail-page PDF requests can intermittently fail with SSL EOF or read timeout; those records remain imported with `document_url` empty instead of blocking the whole refresh.

## 2026-06-24 - EMA complete Guidance and information import milestone

Status: implemented

Summary:
- Changed EMA import semantics from "scientific guideline-like rows only" to the complete official `Guidance and information` JSON dataset.
- Removed the local `_is_guidance_row` keyword/URL filter that reduced the official JSON from 2046 rows to 1101 rows.
- Kept completeness as a mechanical validation rule: every JSON row with both `title` and `general_url` is imported, and PDF enrichment cannot drop records.

Validation:
- Live EMA JSON fetch returned 2046 raw `data` rows; all 2046 had `title` and `general_url`.
- Parser verification returned 2046 EMA documents from the same payload.
- CLI refresh: `python -m app.cli clear-agency EMA; python -m app.cli crawl --agency EMA --no-seed-if-empty` deleted 1101 old EMA records and saved 2046 refreshed EMA records.
- SQLite verification after refresh found 2046 EMA records and 1652 EMA records with `document_url`.
- Full validation passed: `python -m pytest -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 46 tests; `python -m unittest discover -s tests -v` passed with 19 tests.

Notes:
- The user reported seeing 2069 records in the EMA source; the live fetch from this environment returned 2046 on 2026-06-24. The crawler now imports the complete live JSON payload it receives instead of filtering it down to guideline-like rows.

## 2026-06-24 - EMA search-count completeness gate milestone

Status: implemented

Summary:
- Added an EMA search-page count check before refreshing EMA records from the official JSON feed.
- Parses the official EMA search page for the active `Guidance and information` facet count and compares it against both JSON `meta.total_records` and parsed import count.
- Stops the EMA crawler when the official search page reports more records than the JSON feed, preventing a partial EMA refresh from being treated as complete.

Validation:
- Targeted tests: `python -m pytest tests\test_ema_crawler.py -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed with 7 tests.
- Live smoke check found JSON `meta.total_records=2046`, parsed EMA documents `2046`, and EMA search page count `2069`.
- Live crawler smoke check returned 0 records with an explicit completeness warning instead of importing the partial JSON dataset.

Notes:
- This milestone does not delete or refresh existing EMA database records.
- The next EMA milestone should implement a supplemental search-page/index crawler or another authoritative source path to account for the 23-record gap between the JSON feed and the EMA search UI.

## 2026-06-24 - EMA source mismatch investigation milestone

Status: investigated

Summary:
- Rechecked EMA's official `Guidance and information JSON data file` from the EMA website data download page.
- Confirmed the official Guidance JSON endpoint currently returns `meta.total_records=2046` with 2046 data rows.
- Confirmed the EMA search UI can report `Guidance and information` as 2069 records, creating a 23-record gap against the JSON feed.
- Confirmed the missing records are not explained by the first visible search results: examples such as `ICH E22 General considerations for patient preference studies` and `Cookies` are already present in the JSON feed.

Validation:
- Live JSON fetch: `https://www.ema.europa.eu/en/documents/report/general-json-report_en.json` returned 2046 rows with timestamp `2026-06-24T06:21:59Z`.
- Live search-count fetch returned 2069 for the active `Guidance and information` facet when the search page responded successfully.
- Direct search pagination URLs such as `page=1` and `page=2` returned EMA 404 pages, including for other content types such as News.
- Search URLs with additional facet/date/sort parameters also returned EMA 404 pages, so the search UI is not a reliable enumerable source.
- `https://www.ema.europa.eu/sitemap.xml`, despite being referenced by EMA's `robots.txt`, returned an EMA 404 page from this environment.
- Cache-busting query parameters on the Guidance JSON endpoint returned EMA 404 pages; the canonical no-query JSON URL remained the only stable Guidance JSON endpoint.

Notes:
- EMA's website data download page states the JSON files are intended for automated systems and updated twice daily; this remains the preferred data channel.
- The crawler should continue treating the search page as a completeness alarm rather than as the primary data source.
- The next practical path is to identify a stable, allowed source for the 23 search-index-only records, or to document that the official automated Guidance JSON feed is currently 2046 while the public search index reports 2069.

## 2026-06-25 - EMA official JSON authority milestone

Status: implemented

Summary:
- Adopted the user preference that EMA imports should be based on the official website data download JSON file, not on the public EMA search-page count.
- Changed the default EMA crawler path so it no longer fetches or enforces the EMA search-page `Guidance and information` count.
- Kept the search-count parser and completeness validator available only as explicit audit utilities, not as default import gates.

Validation:
- Added a regression test confirming the default EMA crawler does not attach a search-count checker.
- Targeted tests: `python -m pytest tests\test_ema_crawler.py -q --basetemp data\pytest_tmp_verify -p no:cacheprovider` passed.

Notes:
- The authoritative automated EMA source for this project is `https://www.ema.europa.eu/en/documents/report/general-json-report_en.json`.
- Search-page counts should not be used to block JSON imports or force supplemental crawling unless the user explicitly changes this policy later.

## 2026-06-25 - CDE chemical and biologics completeness confirmation milestone

Status: verified

Summary:
- Reconfirmed CDE crawler completeness against the official CDE guidance database filters requested by the user.
- The official CDE API returned 408 records for `适用范围=化学药` and 319 records for `适用范围=生物制品`.
- These two official filtered result sets contain 175 overlapping guidance records, so the deduplicated union is 552 unique CDE guidance records.
- The current crawler returns the same 552 unique records because it crawls both filters and deduplicates by `zdyzIdCODE`.

Validation:
- Live CDE API check: chemical drugs `api_total=408`, fetched 408; biological products `api_total=319`, fetched 319.
- Live overlap check: raw total 727, duplicate overlap 175, unique union 552.
- SQLite check: current local database contains 552 CDE records and 548 records with detected attachment URLs.
- Live crawler check: `CDECrawler().crawl()` returned 552 records with 552 unique reference numbers and 548 detected attachment URLs.
- Confirmed presence of representative records from both screenshots: `981efd549bda05ee430ec550583776fc` for the first chemical-drug row and `9c92f5cfa79fc44da0ac28d2b3a0f6b3` for the first biological-product row.
- Reconfirmed the previously missing example `6b02391b10ae8dab7868d00cadd3cce4` is present.

Notes:
- The expected CDE count for the combined scope is 552 unique records, not 408 + 319 = 727, because some guidance applies to both chemical drugs and biological products.
- Four CDE records still do not expose a detected attachment URL during detail-page enrichment and should remain without `document_url` unless the official detail pages change.
