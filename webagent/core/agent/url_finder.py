"""
Discovers scraping-ready URLs for a (site, query) pair.

Strategy (in priority order):
  1. Known URL pattern registry – instant, no network call.
  2. DuckDuckGo HTML search    – no API key required.
  3. Generic fallback           – constructs /search?q=<query> URL.
"""

import logging
import re
from typing import Dict, List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known URL patterns  (domain → search URL template)
# ---------------------------------------------------------------------------

_PATTERNS: Dict[str, str] = {
    # India e-commerce
    "amazon.in":    "https://www.amazon.in/s?k={q}",
    "flipkart.com": "https://www.flipkart.com/search?q={q}",
    "flipkart.in":  "https://www.flipkart.com/search?q={q}",
    "myntra.com":   "https://www.myntra.com/{q}",
    "snapdeal.com": "https://www.snapdeal.com/search?keyword={q}",
    "meesho.com":   "https://www.meesho.com/search?q={q}",
    "nykaa.com":    "https://www.nykaa.com/search/result/?q={q}",
    "ajio.com":     "https://www.ajio.com/search/?text={q}",
    "tatacliq.com": "https://www.tatacliq.com/search/?searchCategory=all&text={q}",
    # Global e-commerce
    "amazon.com":   "https://www.amazon.com/s?k={q}",
    "ebay.com":     "https://www.ebay.com/sch/i.html?_nkw={q}",
    "walmart.com":  "https://www.walmart.com/search?q={q}",
    "etsy.com":     "https://www.etsy.com/search?q={q}",
    "alibaba.com":  "https://www.alibaba.com/trade/search?SearchText={q}",
    "aliexpress.com": "https://www.aliexpress.com/wholesale?SearchText={q}",
    "bestbuy.com":  "https://www.bestbuy.com/site/searchpage.jsp?st={q}",
    "target.com":   "https://www.target.com/s?searchTerm={q}",
    # Jobs
    "linkedin.com": "https://www.linkedin.com/jobs/search/?keywords={q}",
    "naukri.com":   "https://www.naukri.com/{q}-jobs",
    "indeed.com":   "https://www.indeed.com/jobs?q={q}",
    "glassdoor.com":"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={q}",
    "monster.com":  "https://www.monster.com/jobs/search/?q={q}",
    # Real estate
    "zillow.com":   "https://www.zillow.com/homes/{q}_rb/",
    "magicbricks.com":"https://www.magicbricks.com/property-for-sale/residential-real-estate?proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName={q}",
    "99acres.com":  "https://www.99acres.com/search/property/buy/{q}",
    # Travel
    "booking.com":  "https://www.booking.com/searchresults.html?ss={q}",
    "airbnb.com":   "https://www.airbnb.com/s/{q}/homes",
    "makemytrip.com":"https://www.makemytrip.com/hotels/{q}-hotels.html",
    # Social / News
    "reddit.com":   "https://www.reddit.com/search/?q={q}",
    "twitter.com":  "https://twitter.com/search?q={q}",
    "youtube.com":  "https://www.youtube.com/results?search_query={q}",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_urls(sites: List[str], query: str) -> List[Dict[str, str]]:
    """
    Return a list of dicts:  {site, url, method}
    where method is one of "pattern" | "search" | "fallback".
    """
    results = []
    for site in sites:
        url, method = _resolve(site.lower().lstrip("www."), query)
        results.append({"site": site, "url": url, "method": method})
        logger.info(f"[url_finder] {site} → {url}  ({method})")
    return results


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def _resolve(site: str, query: str) -> tuple:
    """Return (url, method) for a site + query."""
    # 1. Known pattern
    url = _from_pattern(site, query)
    if url:
        return url, "pattern"

    # 2. DuckDuckGo search
    try:
        url = _ddg_search(site, query)
        if url:
            return url, "search"
    except Exception as exc:
        logger.debug(f"[url_finder] DDG search failed for {site}: {exc}")

    # 3. Generic fallback
    q = quote_plus(query)
    return f"https://www.{site}/search?q={q}", "fallback"


def _from_pattern(site: str, query: str) -> Optional[str]:
    """Match site against the pattern registry (exact or suffix match)."""
    q = quote_plus(query)
    for key, tmpl in _PATTERNS.items():
        if site == key or site.endswith("." + key) or key.endswith("." + site):
            return tmpl.format(q=q)
    return None


def _ddg_search(site: str, query: str) -> Optional[str]:
    """Use DuckDuckGo HTML to find the search-results URL for a site."""
    import requests

    search_term = f"site:{site} {query}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": search_term},
        headers=headers,
        timeout=10,
    )

    # Pull any href that belongs to the target site
    pattern = r'href="(https?://(?:www\.)?'+ re.escape(site) + r'[^"]*)"'
    matches = re.findall(pattern, resp.text)
    if matches:
        return matches[0]
    return None
