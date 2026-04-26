"""
Task planner: single AI call → structured JSON plan.

The plan is a list of browser tool steps. Steps that need to interact with
a page element use a ``target`` key (semantic name) instead of a raw CSS
selector.  The heuristic_resolver will translate each target name to an
actual selector at runtime — zero extra AI calls when it succeeds.

If the planner call fails (network error, malformed JSON, empty steps) it
returns None and the caller falls back to the full agent loop.
"""

import json
import logging
import re
from typing import List, Optional

from .llm import LLMClient
from ..heuristic_resolver import KNOWN_TARGETS

logger = logging.getLogger(__name__)

# ── Prompts ───────────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a browser automation planner. "
    "Given a task, output a JSON execution plan — nothing else."
)

_USER_TEMPLATE = """\
Break the following browser task into a precise sequence of tool calls.

Current page URL: {current_url}
IMPORTANT: The browser is ALREADY on this URL. Do NOT add a navigate step unless \
the task requires going to a genuinely different URL. Never navigate to a placeholder \
like example.com — use only real, fully-qualified URLs relevant to the task.

Rules:
- For page elements use "target" (a semantic name) NOT a CSS selector.
- Only use these target names: {targets}
- For navigate steps always include the full URL (https://...).
- Every step MUST include a "verify" condition.
  Use the MOST RELIABLE check for each step — prefer checks that will not be
  fragile due to dynamic content or unexpected URL patterns:
  * navigate       → url_contains with just the bare domain (e.g. "youtube.com")
  * click/press_key that causes navigation → url_changed  (most reliable)
  * click/press_key that does NOT navigate (opens modal, menu) → none
  * fill / hover   → none  (no observable DOM change to check)
  * find_elements / scroll → none
  * page_contains  → only when the exact keyword is guaranteed to appear
  * url_contains   → only for stable path segments, never for query-string values
  If in doubt, use {{"type":"none"}} — a wrong verify breaks the plan.
- Keep the plan minimal — only the steps actually needed.
- Return ONLY valid JSON. No markdown fences, no explanation.

Available tools: navigate, fill, click, press_key, wait_for_load, find_elements, scroll

Verify types:
  {{"type":"none"}}
  {{"type":"url_contains","value":"domain.com"}}
  {{"type":"url_changed"}}
  {{"type":"page_contains","value":"guaranteed text on success page"}}
  {{"type":"page_not_contains","value":"error message text"}}
  {{"type":"element_visible","selector":"css-selector"}}

Output format (YouTube search example — browser already on youtube.com):
{{"steps":[
  {{"tool":"fill","args":{{"target":"search_input","text":"python tutorial"}},"verify":{{"type":"none"}}}},
  {{"tool":"press_key","args":{{"key":"Enter"}},"verify":{{"type":"url_changed"}}}},
  {{"tool":"find_elements","args":{{"target":"results_list"}},"verify":{{"type":"none"}}}}
]}}

Task: {task}"""


# ── Public API ────────────────────────────────────────────────────────────────

def generate_plan(task: str, llm: LLMClient, current_url: str = "") -> Optional[List[dict]]:
    """
    Call the LLM **once** to produce a structured plan for *task*.

    Returns a list of step dicts on success, ``None`` on any failure.
    The caller should fall back to the full agent loop when None is returned.
    """
    prompt = _USER_TEMPLATE.format(
        task=task,
        targets=", ".join(KNOWN_TARGETS),
        current_url=current_url or "unknown",
    )
    try:
        raw = llm.complete_text([
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": prompt},
        ])

        # Strip markdown fences if the model wraps the JSON anyway
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()

        data  = json.loads(raw)
        steps = data.get("steps", [])

        if not isinstance(steps, list) or not steps:
            logger.warning("[planner] Plan has no steps — falling back to agent loop")
            return None

        logger.info(f"[planner] {len(steps)}-step plan generated for: {task!r}")
        return steps

    except Exception as exc:
        logger.warning(f"[planner] Plan generation failed ({exc}) — falling back to agent loop")
        return None
