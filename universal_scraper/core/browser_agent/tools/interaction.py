from playwright.sync_api import Page


def click(page: Page, selector: str = None, x: int = None, y: int = None, index: int = None) -> dict:
    if index is not None:
        elements = page.query_selector_all(
            "a[href], button, input, select, textarea, [onclick], [role='button'], [role='link']"
        )
        if index < len(elements):
            elements[index].click(timeout=10000)
            return {"clicked": f"element_index={index}"}
        return {"error": f"Index {index} out of range ({len(elements)} elements found)"}
    if selector:
        page.click(selector, timeout=10000)
        return {"clicked": selector}
    if x is not None and y is not None:
        page.mouse.click(x, y)
        return {"clicked": f"coordinates=({x},{y})"}
    return {"error": "Provide selector, index, or x/y coordinates"}


def fill(page: Page, selector: str, text: str, clear_first: bool = True) -> dict:
    if clear_first:
        page.fill(selector, "", timeout=10000)
    page.type(selector, text, delay=30)
    return {"filled": selector, "text": text}


def press_key(page: Page, key: str, selector: str = None) -> dict:
    if selector:
        page.focus(selector, timeout=5000)
    page.keyboard.press(key)
    return {"pressed": key}


def hover(page: Page, selector: str) -> dict:
    page.hover(selector, timeout=10000)
    return {"hovered": selector}


def select_option(page: Page, selector: str, value: str = None, label: str = None) -> dict:
    if value is not None:
        page.select_option(selector, value=value, timeout=10000)
        return {"selected": selector, "value": value}
    if label is not None:
        page.select_option(selector, label=label, timeout=10000)
        return {"selected": selector, "label": label}
    return {"error": "Provide value or label"}


def drag_and_drop(page: Page, source: str, target: str) -> dict:
    page.drag_and_drop(source, target, timeout=10000)
    return {"dragged": source, "to": target}
