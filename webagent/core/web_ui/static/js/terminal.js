// ── Terminal log panel ────────────────────────────────────────────────────

function addLogLine(level, message) {
  const term = document.getElementById("terminal");
  const line = document.createElement("div");
  const ts   = new Date().toLocaleTimeString("en-GB", { hour12: false });
  line.className = `log-line level-${level}`;
  line.innerHTML =
    `<span class="log-ts">${escHtml(ts)}</span>` +
    `<span class="log-level">${escHtml(level)}</span>` +
    `<span class="log-msg">${escHtml(message)}</span>`;
  term.appendChild(line);
  term.scrollTop = term.scrollHeight;
}

function clearLogs() {
  document.getElementById("terminal").innerHTML =
    '<div class="term-prompt">$ webagent-ui --ready</div>';
}
