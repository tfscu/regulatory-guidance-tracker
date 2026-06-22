(async () => {
  const columns = [
    "Health Authority",
    "Guidance Name",
    "Summary",
    "Issue Date",
    "FDA Organization",
    "Topic",
    "Guidance Status",
    "Open for Comment",
    "Comment Closing Date on Draft",
    "Guidance PDF Link",
    "Guidance Page Link",
    "Docket Number",
  ];

  const concurrency = 6;
  const normalize = value => String(value || "").replace(/\s+/g, " ").trim();
  const absolute = href => href ? new URL(href, location.origin).href : "";
  const date = value => {
    const text = normalize(value);
    const match = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
    if (!match) return text;
    const year = match[3].length === 2 ? `20${match[3]}` : match[3];
    return `${year}-${match[1].padStart(2, "0")}-${match[2].padStart(2, "0")}`;
  };
  const csv = value => {
    const text = String(value || "");
    return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const isSummaryCandidate = text => {
    const value = normalize(text);
    const lowered = value.toLowerCase();
    if (value.length < 80) return false;
    return ![
      "not for implementation",
      "contains non-binding recommendations",
      "you can submit online",
      "all written comments",
      "was this page helpful",
    ].some(marker => lowered.includes(marker));
  };
  const extractDetailSummary = html => {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const candidates = [
      ...doc.querySelectorAll("main article .col-md-8 p"),
      ...doc.querySelectorAll("main article p"),
      ...doc.querySelectorAll("main p"),
    ];
    const paragraph = candidates.map(node => normalize(node.textContent)).find(isSummaryCandidate);
    return paragraph || "";
  };
  const fetchSummary = async row => {
    if (!row["Guidance Page Link"]) return row;
    try {
      const response = await fetch(row["Guidance Page Link"], { credentials: "same-origin" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const summary = extractDetailSummary(await response.text());
      return { ...row, Summary: summary || row.Summary };
    } catch (error) {
      console.warn(`Summary fetch failed for ${row["Guidance Name"]}:`, error);
      return row;
    }
  };
  const mapWithConcurrency = async (items, worker) => {
    const results = new Array(items.length);
    let next = 0;
    const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
      while (next < items.length) {
        const index = next++;
        results[index] = await worker(items[index], index);
        if ((index + 1) % 25 === 0 || index + 1 === items.length) {
          console.log(`Collected summaries for ${index + 1} / ${items.length} guidance records`);
        }
      }
    });
    await Promise.all(workers);
    return results;
  };

  const rows = Array.from(document.querySelectorAll("table.lcds-datatable--sfgd tbody tr"));
  if (!rows.length) {
    alert("No FDA guidance rows found. Open the FDA guidance search page first.");
    return;
  }

  const info = document.querySelector("#DataTables_Table_0_info")?.textContent || "";
  const match = info.match(/Showing\s+\d+\s+to\s+([\d,]+)\s+of\s+([\d,]+)/i);
  if (match && match[1] !== match[2]) {
    const shouldContinue = confirm(
      `${info}\n\nOnly the visible rows will be exported. Choose "All" in Show entries for the exhaustive FDA export. Continue anyway?`
    );
    if (!shouldContinue) return;
  }

  const tableData = rows.map(row => {
    const cells = Array.from(row.querySelectorAll("td"));
    const summaryLink = cells[0]?.querySelector("a");
    const documentLink = cells[1]?.querySelector("a");
    const docketLink = cells[8]?.querySelector("a");
    const name = normalize(summaryLink?.textContent || cells[0]?.textContent);
    return {
      "Health Authority": "FDA",
      "Guidance Name": name,
      "Summary": name,
      "Issue Date": date(cells[2]?.textContent),
      "FDA Organization": normalize(cells[3]?.textContent),
      "Topic": normalize(cells[4]?.textContent),
      "Guidance Status": normalize(cells[5]?.textContent),
      "Open for Comment": normalize(cells[6]?.textContent),
      "Comment Closing Date on Draft": date(cells[7]?.textContent),
      "Guidance PDF Link": absolute(documentLink?.getAttribute("href")),
      "Guidance Page Link": absolute(summaryLink?.getAttribute("href")),
      "Docket Number": normalize(docketLink?.textContent || cells[8]?.textContent),
    };
  });

  console.log(`Starting detail summary collection for ${tableData.length} FDA guidance records...`);
  const data = await mapWithConcurrency(tableData, fetchSummary);
  const content = [
    columns.map(csv).join(","),
    ...data.map(row => columns.map(column => csv(row[column])).join(",")),
  ].join("\n");
  const blob = new Blob(["\ufeff", content], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "fda_guidance.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
  console.log(`Exported ${data.length} FDA guidance rows with detail-page summaries.`);
})();
