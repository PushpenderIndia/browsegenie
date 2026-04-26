"""
Finds a video card / video result item on the current page.
Strategies ordered from most specific to most general.
"""
from typing import Optional
from playwright.sync_api import Page

# Selectors worth waiting for — combined into one wait so we pay the timeout
# at most once across all of them.
_WAIT_COMBINED = ", ".join([
    'ytd-video-renderer',               # YouTube search results
    'ytd-rich-item-renderer',           # YouTube home feed
    'ytd-compact-video-renderer',       # YouTube sidebar / up-next
    'ytd-grid-video-renderer',          # YouTube channel grid
    '[data-a-target="video-tower-card"]',  # Twitch
    '[class*="clip_thumbnail"]',        # Vimeo
])

_WAIT_TIMEOUT_MS = 5_000

# Instant checks — no waiting, just read what's already rendered.
_INSTANT_STRATEGIES = [
    '.iris_video-vital',
    '[data-target="directory-game-card"]',
    'video.html5-main-video',
    'video.video-stream',
    'video[src^="blob:"]',
    'video[src]',
    'video',
    '[class*="VideoCard"]',
    '[class*="video-card"]',
    '[class*="video_card"]',
    '[class*="VideoItem"]',
    '[class*="video-item"]',
    '[class*="video-result"]',
    '[class*="VideoResult"]',
    'a[href*="watch"]',
]


def resolve(page: Page) -> Optional[str]:
    """Return the CSS selector for the first visible video card on the page."""
    # One combined wait — resolves as soon as any selector becomes visible.
    try:
        page.wait_for_selector(_WAIT_COMBINED, state="visible", timeout=_WAIT_TIMEOUT_MS)
    except Exception:
        pass

    # Now do a precise per-selector check to return the exact matching one.
    for selector in _WAIT_COMBINED.split(", ") + _INSTANT_STRATEGIES:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return selector
        except Exception:
            continue

    return None
