from playwright.sync_api import Page


def wait_for_element(page: Page, selector: str, state: str = "visible", timeout: int = 10000) -> dict:
    try:
        page.wait_for_selector(selector, state=state, timeout=timeout)
        return {"selector": selector, "state": state, "found": True}
    except Exception:
        return {"selector": selector, "state": state, "found": False}


def wait_for_load(page: Page, state: str = "domcontentloaded", timeout: int = 10000) -> dict:
    try:
        page.wait_for_load_state(state, timeout=timeout)
        return {"loaded": True, "state": state, "url": page.url}
    except Exception:
        return {"loaded": False, "state": state, "url": page.url}


def wait_for_url(page: Page, url_pattern: str, timeout: int = 10000) -> dict:
    try:
        page.wait_for_url(url_pattern, timeout=timeout)
        return {"matched": True, "url": page.url}
    except Exception:
        return {"matched": False, "url": page.url}
