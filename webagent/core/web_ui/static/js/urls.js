// ── Multi-URL row management ──────────────────────────────────────────────

/** Rebuild the URL list from an array (agent auto-fill uses this). */
function renderUrlList(urls) {
  const list = document.getElementById("url-list");
  list.innerHTML = "";
  (urls.length ? urls : [""]).forEach((url, i) => _appendUrlRow(list, i, url));
  _syncRemoveButtons();
}

/** Append a single blank URL row. */
function addUrlRow(value = "") {
  const list = document.getElementById("url-list");
  _appendUrlRow(list, list.children.length, value);
  _syncRemoveButtons();
  list.lastElementChild?.querySelector(".url-input")?.focus();
}

function removeUrlRow(idx) {
  const rows = [...document.querySelectorAll(".url-entry")];
  if (rows.length <= 1) return;
  rows[idx]?.remove();
  _reindexRows();
}

/** Collect all non-empty URL values. */
function getUrls() {
  return [...document.querySelectorAll(".url-input")]
    .map(i => i.value.trim())
    .filter(Boolean);
}

// ── Internal helpers ──────────────────────────────────────────────────────

function _appendUrlRow(list, idx, value) {
  const div = document.createElement("div");
  div.className = "url-entry";
  div.dataset.idx = idx;
  div.innerHTML =
    `<span class="url-number">${idx + 1}</span>` +
    `<input type="url" class="url-input" placeholder="https://example.com" ` +
      `value="${escHtml(value)}" autocomplete="off" spellcheck="false" ` +
      `onkeydown="if(event.key==='Enter')startScrape()"/>` +
    `<button class="btn-icon btn-remove-url" onclick="removeUrlRow(${idx})" title="Remove">` +
      `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">` +
        `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>` +
      `</svg></button>`;
  list.appendChild(div);
}

function _reindexRows() {
  [...document.querySelectorAll(".url-entry")].forEach((row, i) => {
    row.dataset.idx = i;
    row.querySelector(".url-number").textContent = i + 1;
    row.querySelector(".btn-remove-url").onclick = () => removeUrlRow(i);
  });
  _syncRemoveButtons();
}

function _syncRemoveButtons() {
  const rows = document.querySelectorAll(".url-entry");
  const show = rows.length > 1;
  rows.forEach(r => {
    r.querySelector(".btn-remove-url").style.display = show ? "flex" : "none";
  });
}
