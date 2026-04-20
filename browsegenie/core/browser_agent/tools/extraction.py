"""Browser data-extraction tools.

get_page_content          — visible page text (raw HTML omitted; use find_elements for DOM queries)
find_elements             — batch CSS-selector query returning element properties in one JS round-trip
get_interactive_elements  — full index list of clickable elements for use with click(index=N)
execute_js                — arbitrary JavaScript evaluation
"""

from playwright.sync_api import Page

from .constants import INTERACTIVE_SEL_JS


def get_page_content(page: Page) -> dict:
    """Return URL, title, and visible text (up to 3 000 chars)."""
    url   = page.url
    title = page.title()
    try:
        body = page.query_selector("body")
        text = (body.inner_text() if body else "")[:3000]
    except Exception:
        text = ""
    return {"url": url, "title": title, "text": text}


def find_elements(page: Page, selector: str, limit: int = 20) -> dict:
    """Find DOM elements matching *selector* and return their properties.

    All element data is fetched in a single page.evaluate() call to avoid
    the per-element round-trip overhead of calling el.evaluate() in a loop.
    """
    try:
        data = page.evaluate("""
            (args) => {
                const all = Array.from(document.querySelectorAll(args.sel));
                return {
                    total: all.length,
                    results: all.slice(0, args.limit).map(el => {
                        const raw = {
                            tag:     el.tagName.toLowerCase(),
                            text:    (el.innerText || '').slice(0, 200).trim() || null,
                            href:    el.href              || null,
                            value:   el.getAttribute('value'),
                            id:      el.id                || null,
                            class:   el.className         || null,
                            visible: el.offsetParent !== null,
                        };
                        return Object.fromEntries(
                            Object.entries(raw).filter(([_, v]) => v !== null && v !== '')
                        );
                    }),
                };
            }
        """, {"sel": selector, "limit": limit})
    except Exception as exc:
        return {"error": str(exc), "selector": selector}

    return {"selector": selector, "total": data["total"], "results": data["results"]}


def get_interactive_elements(page: Page) -> dict:
    """List all interactive elements with their index numbers for use with click(index=N)."""
    elements = page.evaluate(f"""
        () => {{
            const sel = '{INTERACTIVE_SEL_JS}';
            return Array.from(document.querySelectorAll(sel)).slice(0, 60).map((el, i) => ({{
                index:   i,
                tag:     el.tagName.toLowerCase(),
                type:    el.type   || null,
                text:    (el.innerText || el.value || el.placeholder || '').slice(0, 120).trim(),
                href:    el.href   || null,
                id:      el.id     || null,
                name:    el.name   || null,
                visible: el.offsetParent !== null,
            }}));
        }}
    """)
    return {"elements": elements, "count": len(elements)}


def execute_js(page: Page, script: str) -> dict:
    """Evaluate a JavaScript expression and return its result."""
    try:
        result = page.evaluate(script)
        return {"result": str(result)[:5000]}
    except Exception as exc:
        return {"error": str(exc)}
