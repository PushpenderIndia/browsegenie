"""System prompt and per-step page-state snapshot for the browser agent.

SYSTEM_PROMPT defines the agent's behavioural rules (search submission,
element selection, tool preference).

capture_page_state() returns a compact snapshot — URL, up to 30 interactive
elements, and 1 500 chars of visible text — appended to the history after
every step.  The element cap is intentionally lower than the 60-element limit
of the explicit get_interactive_elements tool: the automatic snapshot keeps
per-step token overhead low while still giving the model enough context to
decide its next action.
"""

import json
from typing import TYPE_CHECKING

from ..heuristic_resolver import KNOWN_TARGETS
from ..tools.constants import INTERACTIVE_SEL_JS

# Deferred import to break the circular dependency:
# browser/session.py → (indirectly) → agent/prompts.py
if TYPE_CHECKING:
    from ..browser.session import BrowserSession


SYSTEM_PROMPT = (
    "You are a browser automation agent. Complete the given task using the provided tools.\n"
    "After each action you receive the updated page state: URL, interactive elements, and visible text.\n"
    "\n"
    "Workflow — ALWAYS follow this order:\n"
    "1. Call plan(task=...) FIRST with a description of what to accomplish.\n"
    "   The plan tool generates and executes a step sequence automatically.\n"
    "2. If plan succeeds: call done(summary=...) to finish.\n"
    "3. If plan fails: read the 'message' and 'current_url' in the result, then:\n"
    "   a. Take ONE targeted manual action to fix the blocker (fill, click, navigate, etc.).\n"
    "   b. Then call plan(task=...) again describing the remaining work from the current state.\n"
    "   Repeat until the task is complete.\n"
    "\n"
    "Manual actions — element targeting (use when fixing a plan failure):\n"
    "- Prefer semantic names as the 'selector' value — the system resolves them automatically:\n"
    "  " + ", ".join(sorted(KNOWN_TARGETS)) + "\n"
    "  Examples: fill(selector=\"username_field\", text=\"...\"), click(selector=\"submit_button\")\n"
    "- Fall back to index=N only when no semantic name fits.\n"
    "- Call get_interactive_elements first to see indices when needed.\n"
    "\n"
    "Search forms (when acting manually):\n"
    "- After fill(), submit with press_key(key='Enter') — never click the submit button by index.\n"
    "\n"
    "Completion:\n"
    "- Call done only after plan(task=...) returns success:true, or after you have verified\n"
    "  manually that the task is fully complete."
)

_MAX_TEXT_CHARS = 1500
_MAX_ELEMENTS   = 30


def capture_page_state(browser: "BrowserSession") -> str:
    """Return a compact snapshot of the current page for the LLM context."""
    page = browser.page
    try:
        url   = page.url
        title = page.title()
        body  = page.query_selector("body")
        text  = (body.inner_text() if body else "")[:_MAX_TEXT_CHARS]
        raw   = page.evaluate(f"""
            () => {{
                const sel = '{INTERACTIVE_SEL_JS}';
                return Array.from(document.querySelectorAll(sel))
                    .filter(el => el.offsetParent !== null)
                    .slice(0, {_MAX_ELEMENTS})
                    .map((el, i) => ({{
                        index: i,
                        tag:   el.tagName.toLowerCase(),
                        text:  (el.innerText || el.value || el.placeholder || '').slice(0, 80).trim(),
                        href:  el.href || null,
                        type:  el.type || null,
                    }}));
            }}
        """)
        # Strip null/empty values; visible is omitted — every element in the
        # list is visible by construction (filtered in JS above).
        elements = [{k: v for k, v in el.items() if v} for el in raw]
        return (
            f"URL: {url}\n"
            f"Title: {title}\n\n"
            f"Elements:\n{json.dumps(elements, separators=(',', ':'))}\n\n"
            f"Text:\n{text}"
        )
    except Exception as exc:
        return f"URL: {browser.current_url()}\n[State unavailable: {exc}]"
