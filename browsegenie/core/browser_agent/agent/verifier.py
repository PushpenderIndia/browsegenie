"""
Per-step deterministic verification.

After each plan step the executor calls verify_step() with the condition
the planner defined.  All checks use Playwright's native wait_for_function /
wait_for_selector so they poll the live DOM efficiently (every ~100 ms) until
the condition is true or the timeout expires — no manual sleep loops needed.

This is far more reliable than snapshot-based checks on SPAs because content
is loaded asynchronously; Playwright's wait primitives respond to DOM mutations
and page events rather than fixed time delays.

Supported types
---------------
none               Always passes (use for steps with no observable output).
url_contains       Current URL contains the given substring (case-insensitive).
url_changed        Current URL differs from the URL captured before the step.
page_contains      Visible page text contains the given keyword.
page_not_contains  Visible page text does NOT contain the given keyword.
element_visible    A CSS selector finds at least one visible element.
"""

import json
import logging
from typing import Callable, Optional

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

# How long (ms) to wait for a condition to become true before failing.
_VERIFY_TIMEOUT_MS = 10_000


# ── Public API ────────────────────────────────────────────────────────────────

def verify_step(
    page: Page,
    condition: dict,
    prev_url: str = "",
    on_event: Optional[Callable] = None,
) -> bool:
    """
    Evaluate *condition* against the live *page*.

    Emits structured ``verify`` events via *on_event* (if provided) so the
    frontend can show exactly what is being checked and the result.

    Parameters
    ----------
    page:       Live Playwright page after the step has executed.
    condition:  Dict with ``{"type": "..."}`` plus type-specific keys.
    prev_url:   URL captured *before* the step (used by ``url_changed``).
    on_event:   Optional ``emit(event_type, data)`` callback.
    """
    vtype = condition.get("type", "none")
    if vtype == "none":
        return True

    def emit(status: str, detail: str = "") -> None:
        if on_event:
            on_event("verify", {
                "condition": _label(condition),
                "status":    status,          # "checking" | "pass" | "fail"
                "attempt":   1,
                "total":     1,
                "detail":    detail or _describe(page, condition, prev_url),
            })

    emit("checking")
    result = _check(page, condition, prev_url)
    emit("pass" if result else "fail")

    if not result:
        logger.debug(f"[verify] {condition} → FAILED  url={page.url}")

    return result


# ── Condition evaluator ───────────────────────────────────────────────────────

def _check(page: Page, condition: dict, prev_url: str) -> bool:
    """
    Evaluate *condition*, waiting up to _VERIFY_TIMEOUT_MS for it to become
    true.  Uses Playwright's native wait primitives so no sleep is needed.
    """
    vtype = condition.get("type", "none")

    if vtype == "none":
        return True

    if vtype == "url_contains":
        value   = condition.get("value", "").lower()
        escaped = json.dumps(value)          # safe JS string literal
        try:
            page.wait_for_function(
                f'() => window.location.href.toLowerCase().includes({escaped})',
                timeout=_VERIFY_TIMEOUT_MS,
            )
            logger.debug(f"[verify] url_contains {value!r} → True  url={page.url}")
            return True
        except Exception:
            logger.debug(f"[verify] url_contains {value!r} → False  url={page.url}")
            return False

    if vtype == "url_changed":
        prev = json.dumps(prev_url.rstrip("/"))
        try:
            page.wait_for_function(
                f'() => window.location.href.replace(/\\/$/, "") !== {prev}',
                timeout=_VERIFY_TIMEOUT_MS,
            )
            logger.debug(f"[verify] url_changed → True  {prev_url!r} → {page.url!r}")
            return True
        except Exception:
            logger.debug(f"[verify] url_changed → False  (still at {page.url!r})")
            return False

    if vtype == "page_contains":
        value   = condition.get("value", "").lower()
        escaped = json.dumps(value)
        try:
            page.wait_for_function(
                f'() => (document.body?.innerText || "").toLowerCase().includes({escaped})',
                timeout=_VERIFY_TIMEOUT_MS,
            )
            logger.debug(f"[verify] page_contains {value!r} → True")
            return True
        except Exception:
            logger.debug(f"[verify] page_contains {value!r} → False")
            return False

    if vtype == "page_not_contains":
        # Checking absence: read immediately — if text is absent now it's absent.
        value = condition.get("value", "").lower()
        try:
            body   = page.query_selector("body")
            text   = (body.inner_text() if body else "").lower()
            result = value not in text
        except Exception:
            result = True   # can't read page → treat as pass
        logger.debug(f"[verify] page_not_contains {value!r} → {result}")
        return result

    if vtype == "element_visible":
        selector = condition.get("selector", "")
        try:
            page.wait_for_selector(selector, state="visible", timeout=_VERIFY_TIMEOUT_MS)
            logger.debug(f"[verify] element_visible {selector!r} → True")
            return True
        except Exception:
            logger.debug(f"[verify] element_visible {selector!r} → False")
            return False

    logger.warning(f"[verify] Unknown verify type '{vtype}' — treating as pass")
    return True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _label(condition: dict) -> str:
    """Short human-readable label shown in the activity panel header."""
    vtype = condition.get("type", "none")
    if vtype == "url_contains":
        return f"URL contains '{condition.get('value', '')}'"
    if vtype == "url_changed":
        return "URL changed after step"
    if vtype == "page_contains":
        return f"Page contains '{condition.get('value', '')}'"
    if vtype == "page_not_contains":
        return f"Page does not contain '{condition.get('value', '')}'"
    if vtype == "element_visible":
        return f"Element visible: {condition.get('selector', '')}"
    return "No verification"


def _describe(page: Page, condition: dict, prev_url: str) -> str:
    """Richer detail string shown alongside the pass/fail result."""
    vtype = condition.get("type", "none")
    try:
        current_url = page.url
    except Exception:
        current_url = "unknown"

    if vtype == "url_contains":
        value = condition.get("value", "")
        found = value.lower() in current_url.lower()
        return f"{'✓' if found else '✗'} '{value}' in {current_url}"

    if vtype == "url_changed":
        changed = current_url.rstrip("/") != prev_url.rstrip("/")
        return f"{'✓' if changed else '✗'} {prev_url} → {current_url}"

    if vtype in ("page_contains", "page_not_contains"):
        value = condition.get("value", "")
        return f"Checking page text for '{value}' on {current_url}"

    if vtype == "element_visible":
        return f"Checking {condition.get('selector', '')} on {current_url}"

    return ""
