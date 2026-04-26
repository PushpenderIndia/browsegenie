"""
Heuristic element resolver.

Maps semantic target names to specialist resolver functions.
Each resolver tries an ordered list of CSS / JS strategies to find a
visible element on the live page — zero AI calls.

Usage
-----
from .heuristic_resolver import resolve, KNOWN_TARGETS

selector = resolve(page, "search_input")   # returns CSS selector or None
if selector is None:
    # all heuristics failed → fall back to AI for this step

Adding a new resolver
---------------------
1. Create  heuristic_resolver/<target_name>.py  with a resolve(page) function.
2. Import and register it below.
3. The planner will automatically include the new target in its prompt.
"""

import logging
from typing import Optional

from playwright.sync_api import Page

from .search_input   import resolve as _search_input
from .username_field import resolve as _username_field
from .password_field import resolve as _password_field
from .submit_button  import resolve as _submit_button
from .compose_button import resolve as _compose_button
from .email_to_field import resolve as _email_to_field
from .email_subject  import resolve as _email_subject
from .email_body     import resolve as _email_body
from .results_list   import resolve as _results_list
from .text_input     import resolve as _text_input
from .video_card     import resolve as _video_card

logger = logging.getLogger(__name__)

# ── Registry ─────────────────────────────────────────────────────────────────

_REGISTRY = {
    "search_input":   _search_input,
    "username_field": _username_field,
    "email_field":    _username_field,   # alias
    "password_field": _password_field,
    "submit_button":  _submit_button,
    "login_button":   _submit_button,    # alias
    "compose_button": _compose_button,
    "new_button":     _compose_button,   # alias
    "email_to_field": _email_to_field,
    "email_subject":  _email_subject,
    "email_body":     _email_body,
    "message_body":   _email_body,       # alias
    "results_list":   _results_list,
    "search_results": _results_list,     # alias
    "text_input":     _text_input,
    "video_card":     _video_card,
}

# Exposed to the planner so it can tell the AI which target names exist
KNOWN_TARGETS: list = sorted(_REGISTRY.keys())


# ── Public API ────────────────────────────────────────────────────────────────

def resolve(page: Page, target: str) -> Optional[str]:
    """
    Resolve *target* to a CSS selector on the live *page*.

    Returns the selector string if a matching visible element is found,
    or ``None`` if all strategies fail (caller should fall back to AI).
    """
    resolver = _REGISTRY.get(target)
    if resolver is None:
        logger.debug(f"[heuristic] No resolver registered for target '{target}'")
        return None

    selector = resolver(page)
    if selector:
        logger.debug(f"[heuristic] '{target}' → {selector!r}")
    else:
        logger.debug(f"[heuristic] '{target}' → all strategies failed")
    return selector
