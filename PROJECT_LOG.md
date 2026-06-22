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
