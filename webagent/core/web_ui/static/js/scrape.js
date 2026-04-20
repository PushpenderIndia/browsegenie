// ── Scrape job: submit + SSE stream ──────────────────────────────────────

async function startScrape() {
  const urls     = getUrls();
  const provider = document.getElementById("provider").value;
  const model    = document.getElementById("model").value;
  const apiKey   = document.getElementById("api-key").value.trim();
  const fields   = [...currentFields];
  const format   = document.querySelector("input[name=format]:checked").value;

  if (!urls.length) { setStatus("error", "Please enter at least one URL"); return; }
  if (!model)       { setStatus("error", "Please select a model");         return; }
  if (provider !== "ollama" && !apiKey) {
    setStatus("error", "API key is required for this provider"); return;
  }

  setStatus("running", "Starting…");
  document.getElementById("scrape-btn").disabled = true;
  document.getElementById("results-body").innerHTML =
    '<div class="placeholder-msg"><div class="spinner"></div><span>Scraping…</span></div>';
  document.getElementById("token-bar").classList.remove("visible");
  lastTokenUsage = null;
  currentResult  = null;

  addLogLine("INFO", `Scraping ${urls.length} URL(s)…`);
  urls.forEach(u => addLogLine("INFO", "  → " + u));

  try {
    const res = await fetch("/api/scrape", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ urls, provider, model, api_key: apiKey, fields, format }),
    });
    const { job_id, error } = await res.json();
    if (error) throw new Error(error);
    streamJob(job_id);
  } catch (e) {
    setStatus("error", e.message);
    document.getElementById("scrape-btn").disabled = false;
    addLogLine("ERROR", e.message);
  }
}

function streamJob(jobId) {
  if (activeSource) activeSource.close();
  const es = new EventSource(`/api/stream/${jobId}`);
  activeSource = es;

  es.onmessage = evt => {
    const data = JSON.parse(evt.data);
    if (data.type === "keepalive") return;

    if (data.type === "done") {
      es.close();
      activeSource = null;
      document.getElementById("scrape-btn").disabled = false;

      if (data.error) {
        setStatus("error", "Scraping failed");
        document.getElementById("results-body").innerHTML =
          `<div class="placeholder-msg" style="color:var(--red)">${escHtml(data.error)}</div>`;
      } else {
        currentResult = data.result;
        const n = data.result?.metadata?.items_extracted ?? 0;
        const u = data.result?.metadata?.urls_scraped    ?? 1;
        setStatus("done", `Done — ${n} item(s) from ${u} URL(s)`);
        renderResult(data.result);
        updateTokenUsage(data.result?.token_usage);
      }
      return;
    }

    if (data.type === "log") {
      setStatus("running", data.message.substring(0, 90));
      addLogLine(data.level, data.message);
    }
  };

  es.onerror = () => {
    es.close();
    activeSource = null;
    document.getElementById("scrape-btn").disabled = false;
    setStatus("error", "Connection lost");
    addLogLine("ERROR", "SSE stream closed unexpectedly");
  };
}

function setStatus(state, msg) {
  const dot = document.getElementById("status-dot");
  dot.className = "status-dot";
  dot.classList.add(
    state === "running" ? "dot-running" :
    state === "done"    ? "dot-done"    :
    state === "error"   ? "dot-error"   : "dot-idle"
  );
  document.getElementById("status-text").textContent = msg || "Ready";
}
