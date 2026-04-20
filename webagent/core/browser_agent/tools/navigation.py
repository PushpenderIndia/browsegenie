from playwright.sync_api import Page


def navigate(page: Page, url: str) -> dict:
    page.goto(url, wait_until="load", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    return {"url": page.url, "title": page.title()}


def go_back(page: Page) -> dict:
    page.go_back(wait_until="domcontentloaded", timeout=10000)
    return {"url": page.url}


def go_forward(page: Page) -> dict:
    page.go_forward(wait_until="domcontentloaded", timeout=10000)
    return {"url": page.url}


def reload(page: Page) -> dict:
    page.reload(wait_until="domcontentloaded", timeout=15000)
    return {"url": page.url, "title": page.title()}
