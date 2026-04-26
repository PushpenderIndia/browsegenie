"""
Finds username / email login fields on any page.
Strategies ordered from most specific/reliable to most general.
"""
from typing import Optional
from playwright.sync_api import Page

_STRATEGIES = [
    # Type-based — email inputs are almost always username fields
    'input[type="email"]',
    # Autocomplete hints — very reliable signal
    'input[autocomplete="email"]',
    'input[autocomplete="username"]',
    # Very common name attributes
    'input[name="email"]',
    'input[name="username"]',
    'input[name="user"]',
    'input[name="login"]',
    'input[name="identifier"]',      # Google login
    'input[name="session[username_or_email]"]',  # Twitter/X
    'input[name="emailAddress"]',
    'input[name="userEmail"]',
    'input[name="loginEmail"]',
    'input[name="phone_number"]',    # some sites use phone
    # Common IDs
    'input#email',
    'input#username',
    'input#user',
    'input#login',
    'input#identifier',
    'input#loginEmail',
    'input#ap_email',                # Amazon
    # ARIA labels
    'input[aria-label*="email" i]',
    'input[aria-label*="username" i]',
    'input[aria-label*="phone" i]',
    # Placeholder text
    'input[placeholder*="email" i]',
    'input[placeholder*="username" i]',
    'input[placeholder*="phone or email" i]',  # Instagram
    'input[placeholder*="phone, username" i]', # Instagram alt
    # Data-testid
    'input[data-testid*="username" i]',
    'input[data-testid*="email" i]',
    '[data-testid="login-username"] input',
    # Class-based
    'input.email-input',
    'input[class*="email" i]',
    'input[class*="username" i]',
    # Last resort: first text input inside a login form
    'form[action*="login" i] input[type="text"]:first-of-type',
    'form[action*="signin" i] input[type="text"]:first-of-type',
    'form[id*="login" i] input[type="text"]:first-of-type',
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
