"""User-interaction tools: click, fill, keyboard, hover, select, drag."""

from playwright.sync_api import Page

from .constants import INTERACTIVE_SEL_JS


def click(
    page: Page,
    selector: str = None,
    x: int = None,
    y: int = None,
    index: int = None,
) -> dict:
    """Click by index (visible-element list), CSS selector, or pixel coordinates.

    Index mode uses the same JS visibility filter as capture_page_state and
    get_interactive_elements so that the index the LLM received always resolves
    to the correct DOM node.
    """
    if index is not None:
        handle = page.evaluate_handle(
            """([sel, idx]) => {
                return Array.from(document.querySelectorAll(sel))
                    .filter(el => el.offsetParent !== null)[idx] || null;
            }""",
            [INTERACTIVE_SEL_JS, index],
        )
        el = handle.as_element()
        if el is None:
            return {"error": f"Index {index} out of range (no visible element at that position)"}
        try:
            el.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        el.click(timeout=10000)
        return {"clicked": f"element_index={index}"}

    if selector:
        loc = page.locator(selector).first
        try:
            loc.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        try:
            loc.click(timeout=10000)
        except Exception:
            # JS click as fallback for elements that are present but fail actionability checks
            page.evaluate("(sel) => document.querySelector(sel)?.click()", selector)
        return {"clicked": selector}

    if x is not None and y is not None:
        page.mouse.click(x, y)
        return {"clicked": f"coordinates=({x},{y})"}

    return {"error": "Provide selector, index, or x/y coordinates"}


def fill(page: Page, text: str, selector: str = None, index: int = None, clear_first: bool = True) -> dict:
    """Type *text* into an element identified by *selector* or visible-element *index*."""
    if index is not None:
        handle = page.evaluate_handle(
            """([sel, idx]) => {
                return Array.from(document.querySelectorAll(sel))
                    .filter(el => el.offsetParent !== null)[idx] || null;
            }""",
            [INTERACTIVE_SEL_JS, index],
        )
        el = handle.as_element()
        if el is None:
            return {"error": f"Index {index} out of range (no visible element at that position)"}
        if clear_first:
            el.fill("", timeout=10000)
        el.type(text, delay=30)
        return {"filled": f"element_index={index}", "text": text}

    if selector:
        if clear_first:
            page.fill(selector, "", timeout=10000)
        page.type(selector, text, delay=30)
        return {"filled": selector, "text": text}

    return {"error": "Provide selector or index"}


def press_key(page: Page, key: str, selector: str = None) -> dict:
    """Press *key*, optionally focusing *selector* first."""
    if selector:
        page.focus(selector, timeout=5000)
    page.keyboard.press(key)
    return {"pressed": key}


def hover(page: Page, selector: str) -> dict:
    """Hover over *selector*."""
    page.hover(selector, timeout=10000)
    return {"hovered": selector}


def select_option(page: Page, selector: str, value: str = None, label: str = None) -> dict:
    """Select a dropdown option by *value* or display *label*."""
    if value is not None:
        page.select_option(selector, value=value, timeout=10000)
        return {"selected": selector, "value": value}
    if label is not None:
        page.select_option(selector, label=label, timeout=10000)
        return {"selected": selector, "label": label}
    return {"error": "Provide value or label"}


def drag_and_drop(page: Page, source: str, target: str) -> dict:
    """Drag *source* element to *target* element."""
    page.drag_and_drop(source, target, timeout=10000)
    return {"dragged": source, "to": target}
