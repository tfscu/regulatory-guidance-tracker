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
