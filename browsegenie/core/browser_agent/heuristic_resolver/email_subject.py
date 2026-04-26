"""
Finds the subject line field inside an email composer.
"""
from typing import Optional
from playwright.sync_api import Page

_STRATEGIES = [
    # Semantic name
    'input[name="subject"]',
    'input[name="subjectbox"]',          # Gmail
    'input[name="Subject"]',
    # ARIA labels
    'input[aria-label*="subject" i]',
    '[contenteditable="true"][aria-label*="subject" i]',
    # Placeholder
    'input[placeholder*="subject" i]',
    'input[placeholder*="Subject" ]',
    # IDs
    'input#subject',
    'input#Subject',
    'input[id*="subject" i]',
    # Data attributes
    'input[data-testid*="subject" i]',
    '[data-testid="subject-field"] input',
    # Generic: second text input in a compose form (To → Subject order)
    'form[class*="compose" i] input:nth-of-type(2)',
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
