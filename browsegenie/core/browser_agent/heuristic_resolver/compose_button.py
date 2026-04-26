"""
Finds "Compose", "New", "Create", or "Write" action buttons.
Typically used for Gmail compose, Twitter new tweet, etc.
"""
from typing import Optional
from playwright.sync_api import Page

_CSS_STRATEGIES = [
    # Gmail
    '[gh="cm"]',
    'div[role="button"][data-tooltip*="Compose" i]',
    # Data-testid
    '[data-testid*="compose" i]',
    '[data-testid*="new-post" i]',
    '[data-testid*="tweet" i]',
    # ARIA labels
    '[aria-label*="compose" i]',
    '[aria-label*="new message" i]',
    '[aria-label*="write" i]',
    '[aria-label*="create" i]',
    # Class-based
    'button[class*="compose" i]',
    'button[class*="Compose" ]',
    'a[class*="compose" i]',
    # Floating action buttons (common pattern)
    'button[class*="fab" i]',
    'button[class*="FloatingAction" i]',
]

_TEXT_LABELS = [
    "Compose",
    "New message",
    "New email",
    "Write",
    "Create",
    "New",
    "Post",
    "Tweet",
]


def resolve(page: Page) -> Optional[str]:
    for selector in _CSS_STRATEGIES:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return selector
        except Exception:
            continue

    for label in _TEXT_LABELS:
        try:
            sel = f'[role="button"]:has-text("{label}"), button:has-text("{label}")'
            loc = page.locator(sel).first
            if loc.is_visible():
                return sel
        except Exception:
            continue

    return None
