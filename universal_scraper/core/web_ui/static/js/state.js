// ── Global state shared across all modules ────────────────────────────────
let providers      = {};
let currentResult  = null;
let currentFields  = [];
let activeSource   = null;      // active scrape SSE EventSource
let modelFetchTimer = null;
let lastTokenUsage   = null;
let lastBaTokenUsage = null;
let agentPlan      = null;      // {urls, fields} filled by agent

const DEFAULT_FIELDS = ["title", "url", "description"];
