from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from pathlib import Path
from typing import Iterable


REPORT_COLUMNS = [
    "Health Authority",
    "Guidance Name",
    "Summary",
    "Issue Date",
    "Organization / Committee",
    "Topic",
    "Guidance Status",
    "Open for Comment",
    "Comment Closing Date on Draft",
    "Document Link",
]


def read_records_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def render_html_report(
    records: Iterable[dict[str, str]],
    *,
    title: str = "Guidance Intelligence Dashboard",
    source_url: str = "FDA and EMA official guidance sources",
    source_status: str = "",
) -> str:
    rows = [normalize_report_row(record) for record in records]
    authorities = sorted({row["Health Authority"] for row in rows if row["Health Authority"]})
    orgs = sorted({row["Organization / Committee"] for row in rows if row["Organization / Committee"]})
    topics = sorted({row["Topic"] for row in rows if row["Topic"]})
    statuses = sorted({row["Guidance Status"] for row in rows if row["Guidance Status"]})
    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --paper: #f7f7f2;
      --ink: #16201d;
      --muted: #65706b;
      --line: #c9d0c8;
      --panel: #ffffff;
      --accent: #0f6f63;
      --accent-2: #8b2f24;
      --soft: #e8eee9;
      --warn: #fff4d8;
      --fda: #1f5f99;
      --ema: #0f6f63;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "Aptos", "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    .shell {{ max-width: 1580px; margin: 0 auto; padding: 24px; }}
    header {{
      display: grid;
      grid-template-columns: minmax(280px, 1fr) auto;
      gap: 24px;
      align-items: end;
      border-bottom: 2px solid var(--ink);
      padding-bottom: 18px;
    }}
    h1 {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(34px, 5vw, 64px);
      line-height: 0.95;
      letter-spacing: 0;
    }}
    .source {{ color: var(--muted); font-size: 14px; max-width: 700px; margin-top: 12px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(128px, 1fr));
      gap: 10px;
      min-width: min(680px, 100%);
    }}
    .metric {{ border: 1px solid var(--line); background: var(--panel); padding: 12px; min-height: 88px; }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 28px; line-height: 1; }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 2;
      display: grid;
      grid-template-columns: minmax(220px, 1.4fr) repeat(5, minmax(140px, 1fr)) auto;
      gap: 10px;
      align-items: end;
      margin: 18px 0;
      padding: 12px;
      border: 1px solid var(--line);
      background: rgba(247, 247, 242, 0.96);
      backdrop-filter: blur(10px);
    }}
    label {{
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.07em;
    }}
    input, select, button {{
      width: 100%;
      min-height: 40px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 4px;
      padding: 8px 10px;
      font: inherit;
    }}
    button {{ border-color: var(--ink); background: var(--ink); color: white; cursor: pointer; font-weight: 700; }}
    .notice {{ display: none; border: 1px solid #d9bd72; background: var(--warn); padding: 14px 16px; margin: 18px 0; }}
    .notice.is-visible {{ display: block; }}
    .table-wrap {{ overflow: auto; border: 1px solid var(--line); background: var(--panel); max-height: calc(100vh - 220px); }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1320px; font-size: 14px; }}
    thead th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: var(--ink);
      color: white;
      text-align: left;
      padding: 10px;
      border-right: 1px solid rgba(255,255,255,0.18);
      white-space: nowrap;
    }}
    tbody td {{ padding: 10px; border-top: 1px solid var(--line); vertical-align: top; }}
    tbody tr:hover {{ background: var(--soft); }}
    .name {{ font-weight: 750; min-width: 280px; }}
    .authority {{
      display: inline-block;
      min-width: 44px;
      text-align: center;
      padding: 2px 8px;
      border-radius: 999px;
      color: white;
      font-weight: 800;
      font-size: 12px;
    }}
    .authority.fda {{ background: var(--fda); }}
    .authority.ema {{ background: var(--ema); }}
    .status {{
      display: inline-block;
      min-width: 52px;
      text-align: center;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--soft);
      font-weight: 700;
    }}
    .status.draft {{ border-color: var(--accent-2); color: var(--accent-2); background: #fff1ed; }}
    .comment-open {{ color: var(--accent-2); font-weight: 800; }}
    a {{ color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    .empty {{ padding: 52px 24px; text-align: center; color: var(--muted); border-top: 1px solid var(--line); }}
    @media (max-width: 1100px) {{
      .shell {{ padding: 14px; }}
      header {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
      .toolbar {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (max-width: 620px) {{
      .metrics, .toolbar {{ grid-template-columns: 1fr; }}
      .table-wrap {{ max-height: none; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>{html.escape(title)}</h1>
        <div class="source">Sources: {html.escape(source_url)}</div>
      </div>
      <section class="metrics" aria-label="Inventory metrics">
        <div class="metric"><span>Records</span><strong id="metric-records">0</strong></div>
        <div class="metric"><span>Authorities</span><strong id="metric-authorities">0</strong></div>
        <div class="metric"><span>Open Comment</span><strong id="metric-open">0</strong></div>
        <div class="metric"><span>Topics</span><strong id="metric-topics">0</strong></div>
      </section>
    </header>

    <div id="notice" class="notice">{html.escape(source_status)}</div>

    <section class="toolbar" aria-label="Filters">
      <label>Search<input id="search" type="search" placeholder="Title, summary, topic, organization"></label>
      <label>Authority{render_select("authority", authorities)}</label>
      <label>Organization{render_select("organization", orgs)}</label>
      <label>Topic{render_select("topic", topics)}</label>
      <label>Status{render_select("status", statuses)}</label>
      <label>Comments{render_select("comments", ["Open", "Closed"])}</label>
      <button id="reset" type="button">Reset</button>
    </section>

    <main class="table-wrap">
      <table>
        <thead>
          <tr>{''.join(f'<th>{html.escape(column)}</th>' for column in REPORT_COLUMNS)}</tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
      <div id="empty" class="empty">No guidance records loaded.</div>
    </main>
  </div>

  <script>
    const records = {payload};
    const els = {{
      rows: document.getElementById("rows"),
      empty: document.getElementById("empty"),
      notice: document.getElementById("notice"),
      search: document.getElementById("search"),
      authority: document.getElementById("authority"),
      organization: document.getElementById("organization"),
      topic: document.getElementById("topic"),
      status: document.getElementById("status"),
      comments: document.getElementById("comments"),
      reset: document.getElementById("reset"),
      metricRecords: document.getElementById("metric-records"),
      metricAuthorities: document.getElementById("metric-authorities"),
      metricOpen: document.getElementById("metric-open"),
      metricTopics: document.getElementById("metric-topics")
    }};

    function escapeHtml(value) {{
      return String(value || "").replace(/[&<>"']/g, char => ({{
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }}[char]));
    }}
    function linkCell(url) {{
      if (!url) return "";
      const safeUrl = escapeHtml(url);
      const label = /\\.pdf$|\\/media\\/|\\/documents\\//i.test(url) ? "PDF" : "Page";
      return `<a href="${{safeUrl}}">${{label}}</a>`;
    }}
    function matches(row) {{
      const q = els.search.value.trim().toLowerCase();
      const corpus = [
        row["Health Authority"], row["Guidance Name"], row["Summary"],
        row["Organization / Committee"], row["Topic"], row["Guidance Status"]
      ].join(" ").toLowerCase();
      if (q && !corpus.includes(q)) return false;
      if (els.authority.value && row["Health Authority"] !== els.authority.value) return false;
      if (els.organization.value && row["Organization / Committee"] !== els.organization.value) return false;
      if (els.topic.value && row["Topic"] !== els.topic.value) return false;
      if (els.status.value && row["Guidance Status"] !== els.status.value) return false;
      if (els.comments.value === "Open" && row["Open for Comment"] !== "Yes") return false;
      if (els.comments.value === "Closed" && row["Open for Comment"] === "Yes") return false;
      return true;
    }}
    function render() {{
      const filtered = records.filter(matches);
      els.rows.innerHTML = filtered.map(row => {{
        const authorityClass = `authority ${{String(row["Health Authority"]).toLowerCase()}}`;
        const statusClass = /draft|consultation/i.test(String(row["Guidance Status"])) ? "status draft" : "status";
        const commentClass = row["Open for Comment"] === "Yes" ? "comment-open" : "";
        return `<tr>
          <td><span class="${{authorityClass}}">${{escapeHtml(row["Health Authority"])}}</span></td>
          <td class="name">${{escapeHtml(row["Guidance Name"])}}</td>
          <td>${{escapeHtml(row["Summary"])}}</td>
          <td>${{escapeHtml(row["Issue Date"])}}</td>
          <td>${{escapeHtml(row["Organization / Committee"])}}</td>
          <td>${{escapeHtml(row["Topic"])}}</td>
          <td><span class="${{statusClass}}">${{escapeHtml(row["Guidance Status"])}}</span></td>
          <td class="${{commentClass}}">${{escapeHtml(row["Open for Comment"])}}</td>
          <td>${{escapeHtml(row["Comment Closing Date on Draft"])}}</td>
          <td>${{linkCell(row["Document Link"])}}</td>
        </tr>`;
      }}).join("");
      els.empty.style.display = filtered.length ? "none" : "block";
      els.metricRecords.textContent = filtered.length.toLocaleString();
      els.metricAuthorities.textContent = new Set(filtered.map(row => row["Health Authority"]).filter(Boolean)).size.toLocaleString();
      els.metricOpen.textContent = filtered.filter(row => row["Open for Comment"] === "Yes").length.toLocaleString();
      els.metricTopics.textContent = new Set(filtered.map(row => row["Topic"]).filter(Boolean)).size.toLocaleString();
      els.notice.classList.toggle("is-visible", Boolean(els.notice.textContent.trim()));
    }}
    [els.search, els.authority, els.organization, els.topic, els.status, els.comments].forEach(el => {{
      el.addEventListener("input", render);
      el.addEventListener("change", render);
    }});
    els.reset.addEventListener("click", () => {{
      els.search.value = "";
      els.authority.value = "";
      els.organization.value = "";
      els.topic.value = "";
      els.status.value = "";
      els.comments.value = "";
      render();
    }});
    render();
  </script>
</body>
</html>
"""


def render_select(element_id: str, options: Iterable[str]) -> str:
    rendered = [f'<select id="{html.escape(element_id)}"><option value="">All</option>']
    for option in options:
        safe = html.escape(option)
        rendered.append(f'<option value="{safe}">{safe}</option>')
    rendered.append("</select>")
    return "".join(rendered)


def normalize_report_row(record: dict[str, str]) -> dict[str, str]:
    normalized = {column: str(record.get(column, "") or "") for column in REPORT_COLUMNS}
    normalized["Health Authority"] = normalized["Health Authority"] or str(record.get("Authority", "") or "")
    normalized["Organization / Committee"] = normalized["Organization / Committee"] or str(
        record.get("FDA Organization", "") or record.get("Authority Organization", "") or ""
    )
    normalized["Document Link"] = normalized["Document Link"] or str(
        record.get("Guidance PDF Link", "") or record.get("Guidance Page Link", "") or ""
    )
    return normalized


def write_html_report(
    input_path: Path | list[Path] | None,
    output_path: Path,
    *,
    title: str = "Guidance Intelligence Dashboard",
    source_status: str = "",
) -> int:
    records: list[dict[str, str]] = []
    status = source_status
    input_paths = input_path if isinstance(input_path, list) else ([input_path] if input_path else [])
    missing: list[str] = []
    for path in input_paths:
        if path and path.exists():
            records.extend(read_records_from_csv(path))
        elif path:
            missing.append(str(path))
    if missing:
        status = status or f"Input file not found: {', '.join(missing)}"
    html_text = render_html_report(records, title=title, source_status=status)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    return len(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render guidance records as a static HTML report.")
    parser.add_argument("--input", "-i", action="append", default=None, help="Collector CSV input path. Repeat for multiple sources.")
    parser.add_argument("--output", "-o", default="reports/guidance_dashboard.html", help="HTML output path.")
    parser.add_argument("--title", default="Guidance Intelligence Dashboard", help="Report title.")
    parser.add_argument("--source-status", default="", help="Optional source/data status message.")
    args = parser.parse_args(argv)

    input_paths = [Path(value) for value in (args.input or ["exports/fda_guidance.csv", "exports/ema_guidance.csv"])]
    count = write_html_report(
        input_paths,
        Path(args.output),
        title=args.title,
        source_status=args.source_status,
    )
    print(f"Wrote {count} records to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
