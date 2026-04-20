// ── Result panel rendering ────────────────────────────────────────────────

function renderResult(result) {
  const fmt  = document.querySelector("input[name=format]:checked").value;
  const body = document.getElementById("results-body");
  try {
    if (fmt === "csv" && result.csv_content) {
      body.innerHTML = buildCsvTable(result.csv_content);
    } else {
      body.innerHTML = `<pre style="margin:0">${syntaxHighlight(JSON.stringify(result, null, 2))}</pre>`;
    }
  } catch (e) {
    body.textContent = String(result);
  }
}

function buildCsvTable(csv) {
  const lines = csv.trim().split("\n");
  if (!lines.length) return "<div class='placeholder-msg'>No data</div>";

  const parse = line => {
    const cols = [];
    let cur = "", inQ = false;
    for (const ch of line) {
      if (ch === '"')             inQ = !inQ;
      else if (ch === "," && !inQ){ cols.push(cur); cur = ""; }
      else cur += ch;
    }
    cols.push(cur);
    return cols.map(c => c.replace(/^"|"$/g, "").replace(/""/g, '"'));
  };

  const headers = parse(lines[0]);
  const rows    = lines.slice(1).map(parse);

  const th = headers.map(h => `<th>${escHtml(h)}</th>`).join("");
  const tb = rows.map(r =>
    "<tr>" + headers.map((_, i) =>
      `<td title="${escHtml(r[i]??"")}">${escHtml(r[i]??"")}</td>`
    ).join("") + "</tr>"
  ).join("");

  return `<div class="csv-table-wrap">
    <table class="csv-table">
      <thead><tr>${th}</tr></thead>
      <tbody>${tb}</tbody>
    </table></div>`;
}

function syntaxHighlight(json) {
  return json
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      m => {
        let cls = "json-num";
        if (/^"/.test(m))              cls = /:$/.test(m) ? "json-key" : "json-str";
        else if (/true|false/.test(m)) cls = "json-bool";
        else if (/null/.test(m))       cls = "json-null";
        return `<span class="${cls}">${m}</span>`;
      }
    );
}

function copyResults() {
  if (!currentResult) return;
  const fmt     = document.querySelector("input[name=format]:checked").value;
  const content = fmt === "csv" && currentResult.csv_content
    ? currentResult.csv_content
    : JSON.stringify(currentResult, null, 2);
  navigator.clipboard.writeText(content)
    .then(() => setStatus("done", "Copied to clipboard!"))
    .catch(() => setStatus("error", "Copy failed"));
}

function downloadResults() {
  if (!currentResult) return;
  const fmt = document.querySelector("input[name=format]:checked").value;
  let blob, filename;
  if (fmt === "csv" && currentResult.csv_content) {
    blob     = new Blob([currentResult.csv_content], { type: "text/csv" });
    filename = `scraped_${Date.now()}.csv`;
  } else {
    blob     = new Blob([JSON.stringify(currentResult, null, 2)], { type: "application/json" });
    filename = `scraped_${Date.now()}.json`;
  }
  const a = document.createElement("a");
  a.href  = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}
