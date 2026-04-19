from playwright.sync_api import Page


def get_page_content(page: Page) -> dict:
    url = page.url
    title = page.title()
    try:
        body = page.query_selector("body")
        text = (body.inner_text() if body else "")[:12000]
    except Exception:
        text = ""
    try:
        html = page.content()[:30000]
    except Exception:
        html = ""
    return {"url": url, "title": title, "text": text, "html_snippet": html}


def find_elements(page: Page, selector: str, limit: int = 20) -> dict:
    try:
        elements = page.query_selector_all(selector)
    except Exception as e:
        return {"error": str(e), "selector": selector}
    results = []
    for el in elements[:limit]:
        try:
            item = {
                "tag": el.evaluate("el => el.tagName.toLowerCase()"),
                "text": (el.inner_text() or "")[:200].strip(),
                "href": el.get_attribute("href"),
                "value": el.get_attribute("value"),
                "id": el.get_attribute("id"),
                "class": el.get_attribute("class"),
                "visible": el.is_visible(),
            }
            results.append({k: v for k, v in item.items() if v is not None})
        except Exception:
            pass
    return {"selector": selector, "total": len(elements), "results": results}


def get_interactive_elements(page: Page) -> dict:
    elements = page.evaluate("""
        () => {
            const sel = 'a[href], button, input, select, textarea, [onclick], [role="button"], [role="link"], [tabindex]';
            return Array.from(document.querySelectorAll(sel)).slice(0, 60).map((el, i) => ({
                index: i,
                tag: el.tagName.toLowerCase(),
                type: el.type || null,
                text: (el.innerText || el.value || el.placeholder || '').slice(0, 120).trim(),
                href: el.href || null,
                id: el.id || null,
                name: el.name || null,
                visible: el.offsetParent !== null,
            }));
        }
    """)
    return {"elements": elements, "count": len(elements)}


def execute_js(page: Page, script: str) -> dict:
    try:
        result = page.evaluate(script)
        return {"result": str(result)[:5000]}
    except Exception as e:
        return {"error": str(e)}
