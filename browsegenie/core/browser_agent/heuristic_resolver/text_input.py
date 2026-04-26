"""
Generic single-line text input fallback.
Used when no more specific resolver applies.
Finds the first visible, non-hidden, non-password text input on the page.
"""
from typing import Optional
from playwright.sync_api import Page

_STRATEGIES = [
    # Standard visible text inputs
    'input[type="text"]:not([type="hidden"]):not([readonly])',
    'input:not([type]):not([readonly])',       # input with no type defaults to text
    # Contenteditable single-line areas
    '[contenteditable="true"][role="textbox"]',
    # Textarea as last resort
    'textarea:not([readonly])',
]


def resolve(page: Page) -> Optional[str]:
    for selector in _STRATEGIES:
        try:
            # Use query_selector_all and pick the first visible one
            els = page.query_selector_all(selector)
            for el in els:
                if el.is_visible():
                    # Return the selector (first match wins)
                    return selector
        except Exception:
            continue
    return None
