"""
Finds the "To:" recipient field inside an email composer.
"""
from typing import Optional
from playwright.sync_api import Page

_STRATEGIES = [
    # Gmail
    'input[name="to"]',
    '[data-hovercard-id] input',
    'div[aria-label*="To" ][contenteditable="true"]',
    # Generic email clients
    'input[placeholder*="To" ]',
    'input[placeholder*="recipient" i]',
    'input[aria-label*="To" ]',
    'input[aria-label*="recipient" i]',
    'input[id*="to" i][type="email"]',
    'input[id*="recipient" i]',
    # Contenteditable "To" field (Gmail uses div, not input)
    '[contenteditable="true"][aria-label*="To" ]',
    '[contenteditable="true"][data-tooltip*="To" ]',
    # Name-based
    'input[name="recipient"]',
    'input[name="toAddress"]',
    'input[name="email_to"]',
]


def resolve(page: Page) -> Optional[str]:
    for selector in _STRATEGIES:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return selector
        except Exception:
            continue
    return None
