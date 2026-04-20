// ── AI Agent chat sidebar ─────────────────────────────────────────────────
let _agentSource = null;
let _agentBusy   = false;

// ── Sidebar visibility ────────────────────────────────────────────────────

function toggleSidebar() {
  const sidebar   = document.getElementById("agent-sidebar");
  const toggleBtn = document.getElementById("sidebar-toggle-btn");
  const isMobile  = window.innerWidth <= 1100;

  if (isMobile) {
    const open = sidebar.classList.contains("visible");
    sidebar.classList.toggle("visible", !open);
    sidebar.classList.toggle("hidden",   open);
  } else {
    const hidden = sidebar.classList.contains("hidden");
    sidebar.classList.toggle("hidden", !hidden);
    toggleBtn.classList.toggle("active", hidden);
  }
}

function initSidebar() {
  const sidebar   = document.getElementById("agent-sidebar");
  const toggleBtn = document.getElementById("sidebar-toggle-btn");
  if (window.innerWidth <= 1100) {
    sidebar.classList.add("hidden");
    return;
  }
  // Always open by default on desktop
  sidebar.classList.remove("hidden");
  toggleBtn.classList.add("active");
}

// ── Chat input handlers ───────────────────────────────────────────────────

function onChatKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
  // Auto-resize textarea
  const ta = e.target;
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 110) + "px";
}

async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const text  = input.value.trim();
  if (!text || _agentBusy) return;

  const provider = document.getElementById("provider").value;
  const model    = document.getElementById("model").value;
  const apiKey   = document.getElementById("api-key").value.trim();

  if (!model) { _showAlert("Please select a model first."); return; }
  if (provider !== "ollama" && !apiKey) {
    _showAlert("Please enter an API key first."); return;
  }

  // Show user bubble
  _addUserBubble(text);
  input.value = "";
  input.style.height = "auto";

  _setBusy(true);
  _addTypingIndicator();

  try {
    const res = await fetch("/api/agent/plan", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ requirement: text, provider, model, api_key: apiKey }),
    });
    const { task_id, error } = await res.json();
    if (error) throw new Error(error);
    _streamAgentPlan(task_id);
  } catch (e) {
    _removeTypingIndicator();
    _addAgentBubble(`<span style="color:var(--red)">Error: ${escHtml(e.message)}</span>`);
    _setBusy(false);
  }
}

// ── SSE streaming ─────────────────────────────────────────────────────────

function _streamAgentPlan(taskId) {
  if (_agentSource) _agentSource.close();
  const es = new EventSource(`/api/agent/stream/${taskId}`);
  _agentSource = es;

  es.onmessage = evt => {
    const data = JSON.parse(evt.data);
    if (data.type === "keepalive") return;

    switch (data.type) {
      case "steps_init":
        _removeTypingIndicator();
        _addAgentBubble("On it! Let me plan that for you ✨");
        break;

      case "step_update":
        _handleStepUpdate(data);
        break;

      case "plan_ready":
        _onPlanReady(data.urls, data.fields, data.url_details);
        break;

      case "error":
        _removeTypingIndicator();
        _addAgentBubble(
          `<span style="color:var(--red)">Something went wrong: ${escHtml(data.message)}</span>`
        );
        break;

      case "done":
        es.close();
        _agentSource = null;
        _setBusy(false);
        break;
    }
  };

  es.onerror = () => {
    es.close();
    _agentSource = null;
    _removeTypingIndicator();
    _setBusy(false);
  };
}

// ── Step update → chat bubble ─────────────────────────────────────────────

const _STEP_LABELS = {
  parse:     { running: "Analysing your requirement…",  done: "Requirement analysed" },
  find_urls: { running: "Searching for target URLs…", done: "Found URLs" },
  fill:      { running: "Auto-filling the form…",     done: "Form filled" },
};

function _handleStepUpdate({ step_id, status, title, detail }) {
  const msgId = "step-" + step_id;
  const labels = _STEP_LABELS[step_id] || {};

  if (status === "running") {
    _addAgentBubble(_stepCardHtml("running", labels.running || title, ""), msgId);
  } else if (status === "done") {
    _updateBubble(msgId, _stepCardHtml("done", labels.done || title, detail || ""));
  } else if (status === "error") {
    _updateBubble(msgId, _stepCardHtml("error", title, detail || ""));
  }
}

function _stepCardHtml(status, title, detail) {
  const icon = status === "done" ? "✓" : status === "error" ? "✗" : "";
  return `<div class="step-chat-card ${status}">
    <div class="step-chat-icon">${escHtml(icon)}</div>
    <div class="step-chat-content">
      <div class="step-chat-title">${escHtml(title)}</div>
      ${detail ? `<div class="step-chat-detail">${escHtml(detail)}</div>` : ""}
    </div>
  </div>`;
}

// ── Plan ready ────────────────────────────────────────────────────────────

function _onPlanReady(urls, fields, urlDetails) {
  // Auto-fill main form
  renderUrlList(urls);
  setFields(fields);

  // Build URL rows
  const urlRows = (urlDetails || []).map(r =>
    `<div class="plan-url">↗ <b>${escHtml(r.site)}</b> — ${escHtml(r.url)}</div>`
  ).join("") || urls.map(u => `<div class="plan-url">${escHtml(u)}</div>`).join("");

  // Build field chips
  const chips = fields.map(f =>
    `<span class="plan-field-chip">${escHtml(f)}</span>`
  ).join("") || `<span style="color:var(--text3);font-size:11px">none detected</span>`;

  const cardHtml = `<div class="plan-ready-card">
      <div class="plan-ready-title">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
        Plan ready — starting now…
      </div>
      <div>${urlRows}</div>
      <div class="plan-field-chips">${chips}</div>
    </div>`;

  _addAgentBubble(cardHtml, "plan-result");

  // Auto-execute immediately
  document.querySelector(".main-col").scrollTo({ top: 0, behavior: "smooth" });
  startScrape();
}

// ── DOM helpers ───────────────────────────────────────────────────────────

function _getChatEl() { return document.getElementById("chat-messages"); }

function _scrollChat() {
  const el = _getChatEl();
  requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
}

function _addUserBubble(text) {
  const div = document.createElement("div");
  div.className = "chat-msg user";
  div.innerHTML = `<div class="chat-bubble">${escHtml(text)}</div>`;
  _getChatEl().appendChild(div);
  _scrollChat();
}

function _addAgentBubble(html, id) {
  const div = document.createElement("div");
  div.className = "chat-msg agent";
  if (id) div.id = "agent-msg-" + id;
  div.innerHTML = `<div class="chat-bubble">${html}</div>`;
  _getChatEl().appendChild(div);
  _scrollChat();
  return div;
}

function _updateBubble(id, html) {
  const el = document.getElementById("agent-msg-" + id);
  if (el) { el.querySelector(".chat-bubble").innerHTML = html; _scrollChat(); }
}

function _addTypingIndicator() {
  if (document.getElementById("agent-msg-typing")) return;
  const div = document.createElement("div");
  div.className = "chat-msg agent";
  div.id = "agent-msg-typing";
  div.innerHTML = `<div class="typing-bubble">
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  </div>`;
  _getChatEl().appendChild(div);
  _scrollChat();
}

function _removeTypingIndicator() {
  document.getElementById("agent-msg-typing")?.remove();
}

function _setBusy(busy) {
  _agentBusy = busy;
  document.getElementById("chat-send-btn").disabled = busy;
}

function _showAlert(msg) {
  _addAgentBubble(`<span style="color:var(--yellow)">${escHtml(msg)}</span>`);
}
