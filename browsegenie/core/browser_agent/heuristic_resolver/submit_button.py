"""
Finds form submit / login / sign-in buttons on any page.
Tries semantic attributes first, then text-content matching via JS.
"""
from typing import Optional
from playwright.sync_api import Page

# Pure CSS strategies (fast, no JS)
_CSS_STRATEGIES = [
    # Semantic type — most reliable
    'button[type="submit"]',
    'input[type="submit"]',
    # Data-testid patterns
    '[data-testid*="submit" i]',
    '[data-testid*="login" i]',
    '[data-testid*="signin" i]',
    '[data-testid*="sign-in" i]',
    '[data-testid="LoginButton"]',
    # ARIA labels
    '[aria-label*="sign in" i]',
    '[aria-label*="log in" i]',
    '[aria-label*="login" i]',
    '[aria-label*="submit" i]',
    # Name / ID
    'button#login-button',
    'button#submit',
    'button[name="submit"]',
    # Class-based
    'button.login-button',
    'button.submit-button',
    'button[class*="LoginButton"]',
    'button[class*="submit" i]',
    # Site-specific
    'button[data-action="submit"]',
    '.ap_button_input',              # Amazon
]

# Text-content labels to match (Playwright extended selector syntax)
_TEXT_LABELS = [
    "Sign in",
    "Log in",
    "Login",
    "Submit",
    "Continue",
    "Next",
    "Sign up",
    "Register",
    "Get started",
]


def resolve(page: Page) -> Optional[str]:
    """
    1. Try pure CSS strategies.
    2. Fall back to Playwright :has-text() text matching.
    """
    for selector in _CSS_STRATEGIES:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return selector
        except Exception:
            continue

    # Text-content fallback using Playwright's :has-text() locator
    for label in _TEXT_LABELS:
        try:
            # :has-text() is Playwright-specific but supported by page.locator()
            sel = f'button:has-text("{label}")'
            loc = page.locator(sel).first
            if loc.is_visible():
                return sel
        except Exception:
            continue

    return None
