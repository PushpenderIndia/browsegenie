"""
Finds password input fields on any page.
input[type="password"] covers ~99% of cases — everything else is a fallback.
"""
from typing import Optional
from playwright.sync_api import Page

_STRATEGIES = [
    # THE most universal selector — every login form uses this
    'input[type="password"]',
    # Autocomplete hints
    'input[autocomplete="current-password"]',
    'input[autocomplete="new-password"]',
    # Common name attributes
    'input[name="password"]',
    'input[name="passwd"]',
    'input[name="pass"]',
    'input[name="pwd"]',
    'input[name="passwordField"]',
    # Common IDs
    'input#password',
    'input#passwd',
    'input#pass',
    'input#ap_password',             # Amazon
    # ARIA labels
    'input[aria-label*="password" i]',
    # Placeholder
    'input[placeholder*="password" i]',
    # Data-testid
    'input[data-testid*="password" i]',
    '[data-testid="login-password"] input',
]


def resolve(page: Page) -> Optional[str]:
    """Try each CSS strategy in order. Return first matching visible selector."""
    for selector in _STRATEGIES:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return selector
        except Exception:
            continue
    return None
