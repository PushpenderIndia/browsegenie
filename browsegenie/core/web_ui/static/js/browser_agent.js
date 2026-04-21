let _baSessionId    = null;
let _baSource       = null;
let _baBusy         = false;
let _baLive         = false;   // true while CDP stream is active
let _baMode         = "shared"; // agent-only | shared | human-only

let _baFrames       = [];
let _baCurrentFrame = -1;
let _baPlayTimer    = null;
let _baIsPlaying    = false;

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

  // Read the mode from the UI switcher
  const modeEl = document.querySelector(".ba-mode-btn.active");
  _baMode = modeEl ? modeEl.dataset.mode : "shared";

  try {
    const res = await fetch("/api/browser-agent/start", {
      method:  "POST",
      headers: {"Content-Type": "application/json"},
      body:    JSON.stringify({task, provider, model, api_key: apiKey, headless, control_mode: _baMode}),
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
  _baSetLive(false);
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
    _baSetLive(false);
    _baSetBusy(false);
    _baSetStatus("idle", "Disconnected");
  };
}

function _baHandleEvent(event) {
  switch (event.type) {

    case "connection":
      if (event.data.status === "connected") {
        _baSetLive(true);
        _baLogEntry("info",
          event.data.cdp
            ? "Live browser stream started (CDP screencast)"
            : "Live browser stream started (screenshot mode)"
        );
      } else {
        _baSetLive(false);
      }
      break;

    case "live_frame":
      // Show the CDP frame in the preview during an active session
      if (_baLive) _baRenderLiveFrame(event.data);
      break;

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

    case "control": {
      const { source, action, payload, result } = event.data;
      const tag = source === "human" ? "👤" : "🤖";
      _baLogEntry("control",
        `${tag} ${action}(${_baFmtArgs(payload)}) → ${result.status}`
      );
      break;
    }

    case "tokens":
      updateTokenUsage(event.data, "ba-");
      break;

    case "screenshot":
      // Always store screenshot frames for playback
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
      _baSetLive(false);
      // Switch from live view → screenshot playback
      _baSwitchToPlayback();
      if (_baSource) { _baSource.close(); _baSource = null; }
      break;

    case "error":
      _baSetStatus("error", "Error");
      _baLogEntry("error", event.data.message);
      _baSetBusy(false);
      _baSetLive(false);
      if (_baFrames.length > 1) _baSwitchToPlayback();
      if (_baSource) { _baSource.close(); _baSource = null; }
      break;
  }
}

// ── Live frame rendering (CDP stream) ─────────────────────────────────────

function _baRenderLiveFrame(data) {
  const img   = document.getElementById("ba-screenshot");
  const empty = document.getElementById("ba-preview-empty");
  img.src = "data:image/jpeg;base64," + data.image;
  img.style.display   = "block";
  empty.style.display = "none";

  const urlEl = document.getElementById("ba-page-url");
  if (data.url) {
    urlEl.textContent = data.url;
    urlEl.title = data.url;
  }
}

// ── Switch from live view to playback mode ────────────────────────────────

function _baSwitchToPlayback() {
  _baSetLive(false);
  if (_baFrames.length < 1) return;
  // Jump to last frame
  _baCurrentFrame = _baFrames.length - 1;
  _baRenderFrame(_baCurrentFrame);
  _baRevealPlayback();
}

// ── Screenshot frame store (for playback) ─────────────────────────────────

function _baPushFrame(data) {
  _baFrames.push({
    image:       data.image,
    url:         data.url   || "",
    title:       data.title || "",
    step:        data.step  || 0,
    tool:        data.tool  || "",
    frame_index: _baFrames.length,
  });
  // During live mode we don't update the preview here — live_frame handles it
  if (!_baLive) {
    _baCurrentFrame = _baFrames.length - 1;
    _baRenderFrame(_baCurrentFrame);
  }
}

// ── Render a single screenshot frame ─────────────────────────────────────

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

// ── Human control (click on live preview) ─────────────────────────────────

/**
 * Map a mouse event on the <img> element to 1280×720 viewport coordinates.
 *
 * object-fit:contain means the rendered image may be smaller than the element
 * and centred inside it (letterboxed top/bottom or pillarboxed left/right).
 * We must subtract the blank-space offset before scaling, otherwise clicks in
 * the padding area still produce coordinates and everything is shifted.
 *
 * Returns {x, y} in viewport pixels, or null if the click is outside the
 * actual rendered image area.
 */
function _baViewportCoords(e, img) {
  const rect   = img.getBoundingClientRect();
  const VIEW_W = 1280, VIEW_H = 720;

  // Dimensions of the rendered image inside the element (object-fit:contain)
  const imgAspect  = VIEW_W / VIEW_H;           // 1.7̄8̄
  const elemAspect = rect.width / rect.height;

  let rw, rh, ox = 0, oy = 0;
  if (elemAspect > imgAspect) {
    // Element is wider → pillarboxed (blank left + right)
    rh = rect.height;
    rw = rh * imgAspect;
    ox = (rect.width - rw) / 2;
  } else {
    // Element is taller → letterboxed (blank top + bottom)
    rw = rect.width;
    rh = rw / imgAspect;
    oy = (rect.height - rh) / 2;
  }

  const relX = e.clientX - rect.left - ox;
  const relY = e.clientY - rect.top  - oy;

  // Click is in the blank padding — ignore
  if (relX < 0 || relY < 0 || relX > rw || relY > rh) return null;

  return {
    x: Math.round(relX / rw * VIEW_W),
    y: Math.round(relY / rh * VIEW_H),
  };
}

document.addEventListener("DOMContentLoaded", () => {
  const img = document.getElementById("ba-screenshot");
  if (!img) return;

  img.addEventListener("click", e => {
    if (!_baLive || !_baSessionId || _baMode === "agent-only") return;
    const coords = _baViewportCoords(e, img);
    if (!coords) return;                         // clicked in blank padding
    _baSendControl("click", coords);
    const rect = img.getBoundingClientRect();
    _baShowClickRipple(e.clientX - rect.left, e.clientY - rect.top);
  });

  // Keyboard control when preview is focused
  img.setAttribute("tabindex", "0");
  img.addEventListener("keydown", e => {
    if (!_baLive || !_baSessionId || _baMode === "agent-only") return;
    e.preventDefault();
    _baSendControl("press_key", {key: e.key});
  });
});

async function _baSendControl(action, payload) {
  if (!_baSessionId) return;
  try {
    await fetch(`/api/browser-agent/control/${_baSessionId}`, {
      method:  "POST",
      headers: {"Content-Type": "application/json"},
      body:    JSON.stringify({action, payload}),
    });
  } catch (_) {}
}

function _baShowClickRipple(x, y) {
  const body = document.getElementById("ba-preview-body");
  if (!body) return;
  const ripple = document.createElement("div");
  ripple.className = "ba-click-ripple";
  ripple.style.left = x + "px";
  ripple.style.top  = y + "px";
  body.appendChild(ripple);
  setTimeout(() => ripple.remove(), 600);
}

// ── Mode switcher ─────────────────────────────────────────────────────────

function baSetMode(mode) {
  _baMode = mode;
  document.querySelectorAll(".ba-mode-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  // Push mode to backend if session is active
  if (_baSessionId) {
    fetch(`/api/browser-agent/mode/${_baSessionId}`, {
      method:  "POST",
      headers: {"Content-Type": "application/json"},
      body:    JSON.stringify({mode}),
    }).catch(() => {});
  }
  // Update cursor style on preview image
  const img = document.getElementById("ba-screenshot");
  if (img) {
    img.style.cursor = (_baLive && mode !== "agent-only") ? "crosshair" : "default";
  }
}

// ── LIVE badge state ──────────────────────────────────────────────────────

function _baSetLive(live) {
  _baLive = live;
  const badge = document.getElementById("ba-live-badge");
  if (badge) badge.style.display = live ? "inline-flex" : "none";
  // Update cursor
  const img = document.getElementById("ba-screenshot");
  if (img) {
    img.style.cursor = (live && _baMode !== "agent-only") ? "crosshair" : "default";
  }
}

// ── Log helpers ───────────────────────────────────────────────────────────

function _baLogEntry(type, message) {
  const body  = document.getElementById("ba-log-body");
  const empty = body.querySelector(".ba-empty-log");
  if (empty) empty.remove();

  const ICONS = {
    step:"→", tool:"⚙", result:"↩", info:"ℹ",
    done:"✓", error:"✗", control:"⇄",
  };
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
  _baSetLive(false);

  document.getElementById("ba-log-body").innerHTML =
    '<div class="ba-empty-log">Start a task to see agent activity here.</div>';

  const img = document.getElementById("ba-screenshot");
  img.src = "";
  img.style.display  = "none";
  img.style.cursor   = "default";
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
