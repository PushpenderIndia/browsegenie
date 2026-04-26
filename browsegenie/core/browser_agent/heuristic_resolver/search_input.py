"""
Finds search input fields on any page.
Strategies ordered from most specific/reliable to most general.
"""
from typing import Optional
from playwright.sync_api import Page

_STRATEGIES = [
    # HTML5 semantic type — most reliable signal
    'input[type="search"]',
    # ARIA role
    '[role="searchbox"]',
    # Autocomplete hint
    'input[autocomplete="search"]',
    # Very common name attributes
    'input[name="q"]',               # Google, Bing, many CMSes
    'input[name="query"]',           # very common
    'input[name="search"]',          # very common
    'input[name="s"]',               # WordPress
    'input[name="search_query"]',    # YouTube (legacy)
    'input[name="keyword"]',         # e-commerce
    'input[name="keywords"]',        # e-commerce
    'input[name="term"]',
    'input[name="text"]',
    # Common IDs
    'input#search',
    'input#search-input',
    'input#search_input',
    'input#searchInput',
    'input#query',
    'input#searchBox',
    'input#twotabsearchtextbox',      # Amazon
    # ARIA labels
    'input[aria-label*="search" i]',
    'textarea[aria-label*="search" i]',
    # Placeholder text
    'input[placeholder*="search" i]',
    'input[placeholder*="Search" ]',
    # Data-testid (common in React/Vue apps)
    '[data-testid*="search" i] input',
    '[data-testid="search-input"]',
    'input[data-testid*="search" i]',
    # Class-based (less reliable but covers many SPAs)
    'input.search-input',
    'input.searchInput',
    'input.search-box',
    'input.searchbox',
    'input[class*="SearchInput"]',
    'input[class*="search-input"]',
    # Form context — search is usually inside a search form
    'form[role="search"] input',
    'form[action*="search"] input[type="text"]',
    # Position-based last resorts
    'header input[type="text"]:not([type="hidden"])',
    'nav input[type="text"]:not([type="hidden"])',
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
