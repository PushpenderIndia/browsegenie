import base64
import threading
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext, Playwright


class BrowserSession:
    def __init__(self, headless: bool = True, viewport_width: int = 1280, viewport_height: int = 720):
        self._headless = headless
        self._viewport = {"width": viewport_width, "height": viewport_height}
        self._playwright: Playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None
        self._page: Page = None
        self._lock = threading.Lock()
        self._active = False

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        self._context = self._browser.new_context(
            viewport=self._viewport,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self._page = self._context.new_page()
        self._active = True

    def stop(self) -> None:
        self._active = False
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    @property
    def page(self) -> Page:
        return self._page

    @property
    def is_active(self) -> bool:
        return self._active

    def screenshot_jpeg_b64(self) -> str:
        with self._lock:
            data = self._page.screenshot(type="jpeg", quality=70, full_page=False)
            return base64.b64encode(data).decode()

    def current_url(self) -> str:
        try:
            return self._page.url
        except Exception:
            return ""

    def page_title(self) -> str:
        try:
            return self._page.title()
        except Exception:
            return ""
