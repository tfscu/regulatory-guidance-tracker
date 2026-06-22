# Guidance Collector Plan

Goal: Build a reusable health-authority guidance collector, starting with FDA guidance documents, with exportable records containing guidance name, summary/source page, issue date, FDA organization, topic, guidance status, open-for-comment flag, comment closing date on draft, and PDF link.

## Phase 1 - Source Discovery
Status: complete

- Confirm authoritative FDA source and fields.
- Identify FDA table/data endpoint and any access constraints.

## Phase 2 - FDA Collector Design
Status: in_progress

- Define a small Python package and CLI.
- Normalize FDA rows into a stable schema.
- Keep the collector extensible for EMA, CDE, PMDA, and WHO adapters.

## Phase 3 - Tests First
Status: complete

- Add parser tests using representative FDA DataTables JSON/HTML payloads.
- Verify CSV export and row normalization.

## Phase 4 - Implementation
Status: complete

- Implement FDA JSON client with pagination.
- Implement HTML cleanup and link extraction.
- Implement CLI export to CSV/JSON.

## Phase 5 - Live Verification
Status: complete

- Run unit tests.
- Try a live FDA collection against the official endpoint.
- Document any network limitations and how to run locally.

## Phase 6 - HTML Report
Status: complete

- Add a static HTML report generator for CSV outputs.
- Include analyst-friendly filters, summary metrics, and a dense guidance table.
- Generate the current FDA report page, including a clear source status when live data is unavailable.

## Phase 7 - EMA Collector and Two-Source Display
Status: complete

- Add EMA collector based on EMA's official JSON data files for automated systems.
- Normalize EMA scientific guideline pages into the shared guidance schema.
- Update HTML report display labels and filters so FDA and EMA results can be reviewed together.

## User-Facing Plan

1. Build FDA first using the official FDA guidance search table as the authority.
2. Pull all pages from the FDA DataTables JSON endpoint rather than scraping only visible rows.
3. Normalize each row into one schema suitable for later FDA/EMA/CDE/PMDA/WHO merging.
4. Export CSV by default, with JSON available for downstream automation.
5. Add tests around row parsing, link extraction, pagination behavior, and export columns.
6. Leave clear extension points for the remaining authorities.
