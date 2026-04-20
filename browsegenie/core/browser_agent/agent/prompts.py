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

from ..tools.constants import INTERACTIVE_SEL_JS

# Deferred import to break the circular dependency:
# browser/session.py → (indirectly) → agent/prompts.py
if TYPE_CHECKING:
    from ..browser.session import BrowserSession


SYSTEM_PROMPT = (
    "You are a browser automation agent. Complete the given task using the provided tools.\n"
    "After each action you receive the updated page state: URL, interactive elements, and visible text.\n"
    "\n"
    "Search forms:\n"
    "- After fill(), ALWAYS submit by pressing Enter: press_key(key='Enter').\n"
    "- NEVER try to click a search/submit button by index — search pages have a clear (×) button\n"
    "  near the input that has a lower index than the submit button and will just erase your text.\n"
    "\n"
    "Clicking elements:\n"
    "- Call get_interactive_elements first to see element text and index, then click(index=N).\n"
    "- Read the element text carefully — pick the element whose text matches what you want to click.\n"
    "- Prefer click(selector=...) with a specific CSS selector when the element is identifiable.\n"
    "\n"
    "Efficiency:\n"
    "- Prefer find_elements(selector=...) for targeted DOM lookups over get_page_content.\n"
    "- Only call get_page_content when you need broad full-page text not visible in the state.\n"
    "\n"
    "Completion:\n"
    "- When the task is fully finished, call done with a clear summary."
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
                    .slice(0, {_MAX_ELEMENTS})
                    .map((el, i) => ({{
                        index:   i,
                        tag:     el.tagName.toLowerCase(),
                        text:    (el.innerText || el.value || el.placeholder || '').slice(0, 80).trim(),
                        href:    el.href   || null,
                        type:    el.type   || null,
                        visible: el.offsetParent !== null,
                    }}));
            }}
        """)
        # Strip None values and use compact separators to minimise token count
        elements = [{k: v for k, v in el.items() if v is not None} for el in raw]
        return (
            f"URL: {url}\n"
            f"Title: {title}\n\n"
            f"Elements:\n{json.dumps(elements, separators=(',', ':'))}\n\n"
            f"Text:\n{text}"
        )
    except Exception as exc:
        return f"URL: {browser.current_url()}\n[State unavailable: {exc}]"
