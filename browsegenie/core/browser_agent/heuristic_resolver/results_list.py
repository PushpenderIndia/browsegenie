"""
Finds the main results / items list on a page.
Tries well-known site-specific selectors first, then falls back to
a JS heuristic that detects the largest group of structurally similar siblings.
"""
from typing import Optional
from playwright.sync_api import Page

_CSS_STRATEGIES = [
    # ── Video platforms ──────────────────────────────────────────────────
    'ytd-video-renderer',
    'ytd-rich-item-renderer',
    'ytd-compact-video-renderer',

    # ── Search engines ───────────────────────────────────────────────────
    '.g[data-hveid]',               # Google
    '.tF2Cxc',                      # Google result card
    '.yuRUbf',                      # Google result link block
    '[data-sokoban-container]',     # Google (newer)
    '.b_algo',                      # Bing

    # ── E-commerce ───────────────────────────────────────────────────────
    '[data-component-type="s-search-result"]',   # Amazon
    '.s-result-item[data-asin]',                 # Amazon alt
    '.product-item',
    '[class*="product-card"]',
    '[class*="ProductCard"]',
    '.item-cell',
    '[class*="ItemCard"]',

    # ── Social / news ────────────────────────────────────────────────────
    '[data-testid="tweet"]',
    '[data-testid="cellInnerDiv"]',   # Twitter/X
    'article[role="article"]',        # generic article cards
    '.css-1dbjc4n[data-testid]',      # Twitter fallback

    # ── Developer platforms ──────────────────────────────────────────────
    '[data-testid="results-list"] > li',  # GitHub
    '.repo-list-item',                    # GitHub alt
    '.Box-row',                           # GitHub rows

    # ── Generic patterns ────────────────────────────────────────────────
    'article',
    'ul.results > li',
    'ol.results > li',
    '.result-item',
    '.search-result',
    '[class*="result-item"]',
    '[class*="search-result"]',
    '[class*="ResultItem"]',
    'li[class*="item"]',
]

# JS heuristic: find the element type+class with the most repeated siblings
_JS_HEURISTIC = """
() => {
    const candidates = Array.from(
        document.querySelectorAll('li[class], article[class], div[class]')
    );
    const counts = {};
    candidates.forEach(el => {
        const firstClass = (el.className || '').split(' ').find(c => c.length > 2);
        if (!firstClass) return;
        const key = el.tagName.toLowerCase() + '.' + firstClass;
        counts[key] = (counts[key] || 0) + 1;
    });
    const best = Object.entries(counts)
        .filter(([, n]) => n >= 3)
        .sort(([, a], [, b]) => b - a)[0];
    return best ? best[0] : null;
}
"""


def resolve(page: Page) -> Optional[str]:
    # 1. Try known CSS strategies
    for selector in _CSS_STRATEGIES:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return selector
        except Exception:
            continue

    # 2. JS heuristic fallback
    try:
        selector = page.evaluate(_JS_HEURISTIC)
        if selector:
            count = len(page.query_selector_all(selector))
            if count >= 3:
                return selector
    except Exception:
        pass

    return None
