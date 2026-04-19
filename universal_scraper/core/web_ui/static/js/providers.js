// ── Provider + model dropdown management ─────────────────────────────────

const _LS_KEY          = provider => `universal-scraper-${provider}`;
const _LS_PROVIDER_KEY = "universal-scraper-provider";
const _LS_MODEL_KEY    = provider => `universal-scraper-model-${provider}`;

// ── localStorage helpers ──────────────────────────────────────────────────

function _saveKey(provider, value) {
  if (!provider || provider === "ollama") return;
  if (value) localStorage.setItem(_LS_KEY(provider), value);
  else        localStorage.removeItem(_LS_KEY(provider));
}

function _loadKey(provider) {
  return localStorage.getItem(_LS_KEY(provider)) || "";
}

// ── Provider select ───────────────────────────────────────────────────────

function buildProviderSelect() {
  const sel      = document.getElementById("provider");
  const savedKey = localStorage.getItem(_LS_PROVIDER_KEY);
  sel.innerHTML  = "";
  for (const [key, cfg] of Object.entries(providers)) {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = cfg.name;
    sel.appendChild(opt);
  }
  if (savedKey && providers[savedKey]) sel.value = savedKey;
}

async function onProviderChange() {
  const key = document.getElementById("provider").value;
  localStorage.setItem(_LS_PROVIDER_KEY, key);
  const cfg = providers[key];
  if (!cfg) return;

  const keyInput = document.getElementById("api-key");
  keyInput.placeholder = cfg.placeholder;

  // Priority: env var (server) > localStorage > empty
  const stored = _loadKey(key);
  keyInput.value = cfg.saved_key || stored || "";

  const hint = document.getElementById("key-hint");
  if (key === "ollama") {
    hint.innerHTML = "No API key needed &nbsp;·&nbsp; <a href='" + cfg.docs_url + "' target='_blank'>Ollama setup →</a>";
  } else if (cfg.saved_key) {
    hint.innerHTML = "Key loaded from environment &nbsp;·&nbsp; <a href='" + cfg.docs_url + "' target='_blank'>Manage →</a>";
  } else if (stored) {
    hint.innerHTML = "Key loaded from browser storage &nbsp;·&nbsp; <a href='#' onclick='_clearStoredKey(event)'>Clear</a>";
  } else {
    hint.innerHTML = "<a href='" + cfg.docs_url + "' target='_blank'>Get API key →</a>";
  }

  await refreshModels();
}

/** Called when the user edits the API key field — persist to localStorage. */
function onApiKeyInput() {
  const provider = document.getElementById("provider").value;
  const value    = document.getElementById("api-key").value.trim();
  _saveKey(provider, value);

  // Update hint
  const cfg   = providers[provider] || {};
  const hint  = document.getElementById("key-hint");
  if (provider === "ollama") return;
  if (cfg.saved_key) return; // env var takes precedence, don't overwrite hint
  hint.innerHTML = value
    ? "Key saved in browser &nbsp;·&nbsp; <a href='#' onclick='_clearStoredKey(event)'>Clear</a>"
    : "<a href='" + (cfg.docs_url || "#") + "' target='_blank'>Get API key →</a>";

  clearTimeout(modelFetchTimer);
  modelFetchTimer = setTimeout(refreshModels, 800);
}

function _clearStoredKey(e) {
  e.preventDefault();
  const provider = document.getElementById("provider").value;
  localStorage.removeItem(_LS_KEY(provider));
  document.getElementById("api-key").value = "";
  onProviderChange();
}

// ── Model dropdown ────────────────────────────────────────────────────────

async function refreshModels() {
  const provider = document.getElementById("provider").value;
  const apiKey   = document.getElementById("api-key").value.trim();
  const modelSel = document.getElementById("model");
  const spinner  = document.getElementById("model-spinner");

  spinner.style.display = "flex";
  modelSel.disabled = true;

  try {
    const params = new URLSearchParams({ provider });
    if (apiKey) params.set("api_key", apiKey);

    const data        = await fetch("/api/models?" + params).then(r => r.json());
    const models      = data.models || [];
    const savedModel  = localStorage.getItem(_LS_MODEL_KEY(provider));

    modelSel.innerHTML = "";
    if (!models.length) {
      const opt = document.createElement("option");
      opt.textContent = "No models found";
      modelSel.appendChild(opt);
    } else {
      models.forEach(m => {
        const opt = document.createElement("option");
        opt.value = opt.textContent = m;
        modelSel.appendChild(opt);
      });
      if (savedModel && models.includes(savedModel)) modelSel.value = savedModel;
    }
  } catch (e) {
    addLogLine("ERROR", "Failed to load models: " + e);
  } finally {
    spinner.style.display = "none";
    modelSel.disabled = false;
  }
}

function onModelChange() {
  const provider = document.getElementById("provider").value;
  const model    = document.getElementById("model").value;
  if (model) localStorage.setItem(_LS_MODEL_KEY(provider), model);
}

function toggleKey() {
  const inp = document.getElementById("api-key");
  inp.type = inp.type === "password" ? "text" : "password";
}
