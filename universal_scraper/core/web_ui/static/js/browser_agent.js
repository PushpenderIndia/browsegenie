let _baSessionId   = null;
let _baSource      = null;
let _baBusy        = false;

let _baFrames      = [];
let _baCurrentFrame = -1;
let _baPlayTimer   = null;
let _baIsPlaying   = false;

// ── Tab switching ─────────────────────────────────────────────────────────

function switchMainTab(tab) {
  const scraper    = document.getElementById("tab-scraper");
  const baPanel    = document.getElementById("tab-browser-agent");
  const btnScraper = document.getElementById("main-tab-scraper");
  const btnBa      = document.getElementById("main-tab-browser-agent");
  const sidebar    = document.getElementById("agent-sidebar");
  const toggleBtn  = document.getElementById("sidebar-toggle-btn");

  if (tab === "scraper") {
    scraper.style.display = "";
    baPanel.style.display = "none";
    btnScraper.classList.add("active");
    btnBa.classList.remove("active");
    if (window.innerWidth > 1100) {
      sidebar.classList.remove("hidden");
      toggleBtn.classList.add("active");
    }
  } else {
    scraper.style.display = "none";
    baPanel.style.display = "";
    btnScraper.classList.remove("active");
    btnBa.classList.add("active");
    sidebar.classList.add("hidden");
    toggleBtn.classList.remove("active");
  }
}

// ── Agent lifecycle ───────────────────────────────────────────────────────

async function baStart() {
  const task     = (document.getElementById("ba-task").value || "").trim();
  const provider = document.getElementById("provider").value;
  const model    = document.getElementById("model").value;
  const apiKey   = (document.getElementById("api-key").value || "").trim();
  const headless = document.getElementById("ba-headless").checked;

  if (!task)  { _baLogEntry("error", "Please describe a task first."); return; }
  if (!model) { _baLogEntry("error", "Please select a model first."); return; }
  if (provider !== "ollama" && !apiKey) {
    _baLogEntry("error", "Please enter an API key first."); return;
  }

  _baSetBusy(true);
  _baClearAll();
  _baSetStatus("running", "Starting agent…");

  try {
    const res = await fetch("/api/browser-agent/start", {
      method:  "POST",
      headers: {"Content-Type": "application/json"},
      body:    JSON.stringify({task, provider, model, api_key: apiKey, headless}),
    });
    const { session_id, error } = await res.json();
    if (error) throw new Error(error);
    _baSessionId = session_id;
    _baConnect(session_id);
  } catch (e) {
    _baSetBusy(false);
    _baSetStatus("error", "Failed to start");
    _baLogEntry("error", "Error: " + e.message);
  }
}

async function baStop() {
  _baStopPlayTimer();
  if (_baSource) { _baSource.close(); _baSource = null; }
  if (_baSessionId) {
    try { await fetch(`/api/browser-agent/stop/${_baSessionId}`, {method: "POST"}); } catch (_) {}
    _baSessionId = null;
  }
  _baSetBusy(false);
  _baSetStatus("idle", "Stopped");
}

// ── SSE connection ────────────────────────────────────────────────────────

function _baConnect(sessionId) {
  if (_baSource) _baSource.close();
  const es = new EventSource(`/api/browser-agent/stream/${sessionId}`);
  _baSource = es;

  es.onmessage = evt => {
    const event = JSON.parse(evt.data);
    if (event.type === "keepalive") return;
    _baHandleEvent(event);
  };

  es.onerror = () => {
    es.close();
    _baSource = null;
    _baSetBusy(false);
    _baSetStatus("idle", "Disconnected");
  };
}

function _baHandleEvent(event) {
  switch (event.type) {
    case "start":
      _baLogEntry("info", "Task: " + event.data.task);
      break;

    case "step":
      _baLogEntry("step", `Step ${event.data.step}`);
      _baSetStatus("running", `Step ${event.data.step}`);
      break;

    case "tool_call":
      _baLogEntry("tool", `${event.data.tool}(${_baFmtArgs(event.data.args)})`);
      break;

    case "tool_result": {
      const s = JSON.stringify(event.data.result);
      _baLogEntry("result", s.length > 200 ? s.slice(0, 200) + "…" : s);
      break;
    }

    case "tokens":
      updateTokenUsage(event.data, "ba-");
      break;

    case "screenshot":
      _baPushFrame(event.data);
      break;

    case "log":
      _baLogEntry("info", event.data.message);
      break;

    case "done":
      _baSetStatus("done", "Task complete");
      _baLogEntry("done", event.data.summary);
      _baShowResult(event.data);
      _baSetBusy(false);
      _baRevealPlayback();
      if (_baSource) { _baSource.close(); _baSource = null; }
      break;

    case "error":
      _baSetStatus("error", "Error");
      _baLogEntry("error", event.data.message);
      _baSetBusy(false);
      if (_baFrames.length > 1) _baRevealPlayback();
      if (_baSource) { _baSource.close(); _baSource = null; }
      break;
  }
}

// ── Screenshot frame store ────────────────────────────────────────────────

function _baPushFrame(data) {
  _baFrames.push({
    image:       data.image,
    url:         data.url   || "",
    title:       data.title || "",
    step:        data.step  || 0,
    tool:        data.tool  || "",
    frame_index: _baFrames.length,
  });
  _baCurrentFrame = _baFrames.length - 1;
  _baRenderFrame(_baCurrentFrame);
}

// ── Render a single frame ─────────────────────────────────────────────────

function _baRenderFrame(idx) {
  const frame = _baFrames[idx];
  if (!frame) return;

  const img   = document.getElementById("ba-screenshot");
  const empty = document.getElementById("ba-preview-empty");
  img.src = "data:image/jpeg;base64," + frame.image;
  img.style.display   = "block";
  empty.style.display = "none";

  const urlEl = document.getElementById("ba-page-url");
  urlEl.textContent = frame.url;
  urlEl.title = frame.url;
}

// ── Playback controls ─────────────────────────────────────────────────────

function _baRevealPlayback() {
  if (_baFrames.length < 2) return;
  document.getElementById("ba-playback-wrap").style.display = "";
  _baUpdatePlaybackUI();
}

function _baUpdatePlaybackUI() {
  const total   = _baFrames.length;
  const current = _baCurrentFrame;
  if (total === 0) return;

  const slider  = document.getElementById("ba-timeline");
  slider.max    = total - 1;
  slider.value  = current;

  document.getElementById("ba-frame-counter").textContent =
    `${current + 1} / ${total}`;

  const frame = _baFrames[current];
  if (frame) {
    const label = frame.tool
      ? `step ${frame.step} · ${frame.tool}`
      : frame.step > 0 ? `step ${frame.step}` : "initial";
    document.getElementById("ba-frame-label").textContent = label;
  }
}

function baSeekFrame(idx) {
  _baStopPlayTimer();
  _baCurrentFrame = parseInt(idx);
  _baRenderFrame(_baCurrentFrame);
  _baUpdatePlaybackUI();
}

function baPlayPause() {
  if (_baIsPlaying) {
    _baStopPlayTimer();
    return;
  }
  if (_baCurrentFrame >= _baFrames.length - 1) _baCurrentFrame = 0;
  _baIsPlaying = true;
  document.getElementById("ba-play-btn").innerHTML = "⏸";
  _baPlayTimer = setInterval(() => {
    if (_baCurrentFrame < _baFrames.length - 1) {
      _baCurrentFrame++;
      _baRenderFrame(_baCurrentFrame);
      _baUpdatePlaybackUI();
    } else {
      _baStopPlayTimer();
    }
  }, 650);
}

function _baStopPlayTimer() {
  clearInterval(_baPlayTimer);
  _baPlayTimer  = null;
  _baIsPlaying  = false;
  const btn = document.getElementById("ba-play-btn");
  if (btn) btn.innerHTML = "▶";
}

function baFirstFrame() {
  _baStopPlayTimer();
  _baCurrentFrame = 0;
  _baRenderFrame(0);
  _baUpdatePlaybackUI();
}

function baLastFrame() {
  _baStopPlayTimer();
  _baCurrentFrame = _baFrames.length - 1;
  _baRenderFrame(_baCurrentFrame);
  _baUpdatePlaybackUI();
}

function baPrevFrame() {
  _baStopPlayTimer();
  if (_baCurrentFrame > 0) {
    _baCurrentFrame--;
    _baRenderFrame(_baCurrentFrame);
    _baUpdatePlaybackUI();
  }
}

function baNextFrame() {
  _baStopPlayTimer();
  if (_baCurrentFrame < _baFrames.length - 1) {
    _baCurrentFrame++;
    _baRenderFrame(_baCurrentFrame);
    _baUpdatePlaybackUI();
  }
}

// ── Log helpers ───────────────────────────────────────────────────────────

function _baLogEntry(type, message) {
  const body  = document.getElementById("ba-log-body");
  const empty = body.querySelector(".ba-empty-log");
  if (empty) empty.remove();

  const ICONS = {step:"→", tool:"⚙", result:"↩", info:"ℹ", done:"✓", error:"✗"};
  const div = document.createElement("div");
  div.className = `ba-log-entry ba-log-${type}`;
  div.innerHTML =
    `<span class="ba-log-icon">${ICONS[type] || "·"}</span>` +
    `<span class="ba-log-msg">${escHtml(message)}</span>`;
  body.appendChild(div);
  body.scrollTop = body.scrollHeight;
}

function _baFmtArgs(args) {
  if (!args || typeof args !== "object") return "";
  return Object.entries(args)
    .map(([k, v]) => {
      const s = typeof v === "string" ? `"${v.slice(0, 40)}"` : String(v).slice(0, 40);
      return `${k}=${s}`;
    })
    .join(", ");
}

// ── Status helpers ────────────────────────────────────────────────────────

function _baSetStatus(state, text) {
  const map = {running:"dot-running", done:"dot-done", error:"dot-error", idle:"dot-idle"};
  document.getElementById("ba-status-dot").className = "status-dot " + (map[state] || "dot-idle");
  document.getElementById("ba-status-text").textContent = text;
}

function _baSetBusy(busy) {
  _baBusy = busy;
  document.getElementById("ba-start-btn").disabled = busy;
  document.getElementById("ba-stop-btn").disabled  = !busy;
}

// ── Reset ─────────────────────────────────────────────────────────────────

function _baClearAll() {
  _baFrames       = [];
  _baCurrentFrame = -1;
  _baStopPlayTimer();

  document.getElementById("ba-log-body").innerHTML =
    '<div class="ba-empty-log">Start a task to see agent activity here.</div>';

  const img = document.getElementById("ba-screenshot");
  img.src = "";
  img.style.display = "none";
  document.getElementById("ba-preview-empty").style.display = "";
  document.getElementById("ba-page-url").textContent = "";

  lastBaTokenUsage = null;
  const baTokenBar = document.getElementById("ba-token-bar");
  if (baTokenBar) baTokenBar.classList.remove("visible");

  document.getElementById("ba-playback-wrap").style.display = "none";
  const slider = document.getElementById("ba-timeline");
  slider.value = 0;
  slider.max   = 0;
  document.getElementById("ba-frame-counter").textContent = "0 / 0";
  document.getElementById("ba-frame-label").textContent   = "";

  _baHideResult();
}

function baClearLog() { _baClearAll(); }

function _baHideResult() {
  document.getElementById("ba-result-section").style.display = "none";
}

function _baShowResult(data) {
  const section = document.getElementById("ba-result-section");
  const body    = document.getElementById("ba-result-body");
  body.innerHTML = "";

  if (data.summary) {
    const p = document.createElement("div");
    p.className   = "ba-result-summary";
    p.textContent = data.summary;
    body.appendChild(p);
  }

  if (data.data && Object.keys(data.data).length > 0) {
    const pre = document.createElement("pre");
    pre.className   = "ba-result-data";
    pre.textContent = JSON.stringify(data.data, null, 2);
    body.appendChild(pre);
  }

  section.style.display = "";
}
