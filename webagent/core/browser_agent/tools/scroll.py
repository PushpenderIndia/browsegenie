from playwright.sync_api import Page


def scroll(page: Page, direction: str = "down", pixels: int = 500) -> dict:
    mapping = {
        "down":  f"window.scrollBy(0, {pixels})",
        "up":    f"window.scrollBy(0, -{pixels})",
        "right": f"window.scrollBy({pixels}, 0)",
        "left":  f"window.scrollBy(-{pixels}, 0)",
    }
    script = mapping.get(direction)
    if not script:
        return {"error": f"Invalid direction '{direction}'. Use: down, up, left, right"}
    page.evaluate(script)
    return {"scrolled": direction, "pixels": pixels}


def scroll_to_element(page: Page, selector: str) -> dict:
    el = page.query_selector(selector)
    if el:
        el.scroll_into_view_if_needed()
        return {"found": True, "selector": selector}
    return {"found": False, "selector": selector}


def scroll_to_bottom(page: Page) -> dict:
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    return {"action": "scroll_to_bottom"}


def scroll_to_top(page: Page) -> dict:
    page.evaluate("window.scrollTo(0, 0)")
    return {"action": "scroll_to_top"}
