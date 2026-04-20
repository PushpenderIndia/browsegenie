// ── Token usage bar + modal ────────────────────────────────────────────────
//
// `prefix` is an optional ID prefix string (e.g. "ba-") that selects which
// bar to update. Pass no argument (or "") to target the Scraper tab bar.

function updateTokenUsage(usage, prefix) {
  if (!usage) return;
  const p = prefix || "";

  if (p === "ba-") lastBaTokenUsage = usage;
  else             lastTokenUsage   = usage;

  const bar   = document.getElementById(p + "token-bar");
  const total = document.getElementById(p + "token-total");
  const inp   = document.getElementById(p + "token-in");
  const out   = document.getElementById(p + "token-out");
  const cache = document.getElementById(p + "token-cache");
  if (!bar) return;

  bar.classList.add("visible");
  total.textContent = fmt(usage.total_tokens);
  inp.textContent   = fmt(usage.total_prompt_tokens);
  out.textContent   = fmt(usage.total_completion_tokens);

  if (usage.cache_hits > 0) {
    cache.style.display = "inline-block";
    cache.textContent   = `${usage.cache_hits} cache hit${usage.cache_hits > 1 ? "s" : ""}`;
  } else {
    cache.style.display = "none";
  }
}

function openTokenModal(prefix) {
  const usage = (prefix === "ba-") ? lastBaTokenUsage : lastTokenUsage;
  if (!usage) return;
  document.getElementById("token-modal-body").innerHTML = _buildModalBody(usage);
  document.getElementById("token-modal").classList.add("open");
}

function closeTokenModal() {
  document.getElementById("token-modal").classList.remove("open");
}

function onModalOverlayClick(e) {
  if (e.target === document.getElementById("token-modal")) closeTokenModal();
}

function _buildModalBody(u) {
  const statCards = [
    { label: "Total Tokens",      value: fmt(u.total_tokens),            accent: true },
    { label: "Prompt Tokens",     value: fmt(u.total_prompt_tokens),     accent: false },
    { label: "Completion Tokens", value: fmt(u.total_completion_tokens), accent: false },
    { label: "API Calls",         value: u.api_calls,                    accent: false },
  ].map(({ label, value, accent }) =>
    `<div class="stat-card">
       <div class="stat-label">${label}</div>
       <div class="stat-value${accent ? " accent" : ""}">${value}</div>
     </div>`
  ).join("");

  const calls = (u.calls || []).map((c, i) => {
    const cached = c.from_cache;
    const rows = cached ? "" : [
      ["Prompt",     fmt(c.prompt_tokens)     + " tokens"],
      ["Completion", fmt(c.completion_tokens) + " tokens"],
      ["Total",      fmt(c.total_tokens)      + " tokens"],
    ].map(([k, v]) =>
      `<div class="call-row"><span>${k}</span><span>${v}</span></div>`
    ).join("");

    return `<div class="call-card">
      <div class="call-header">
        <span class="call-num">Call #${i + 1}</span>
        <span class="call-model">${escHtml(c.model)}</span>
        <span class="call-badge ${cached ? "badge-cache" : "badge-api"}">${cached ? "Cache" : "API"}</span>
      </div>
      ${cached
        ? `<div class="call-row" style="color:var(--accent)"><span>Served from local cache — no tokens used</span></div>`
        : rows}
    </div>`;
  }).join("");

  return `
    <div class="stat-grid">${statCards}</div>
    ${u.cache_hits > 0
      ? `<p style="font-size:12px;color:var(--accent);margin-bottom:14px">
           ✓ ${u.cache_hits} request${u.cache_hits > 1 ? "s were" : " was"} served from cache.
         </p>`
      : ""}
    <div class="section-title">Call Details</div>
    ${calls || '<p style="color:var(--text3);font-size:13px">No calls recorded.</p>'}
  `;
}
