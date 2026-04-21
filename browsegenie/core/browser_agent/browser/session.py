import base64
import queue
import subprocess
import sys
import threading
from typing import Callable, Optional

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext, Playwright


def _ensure_playwright_browsers():
    """Auto-install Chromium if not already installed."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
    except Exception:
        print("BrowseGenie: Installing Chromium browser (one-time setup)...")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True
        )


_ensure_playwright_browsers()


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
        # CDP screencast state
        self._cdp_session = None
        self._screencast_active = False
        self._screencast_callback: Optional[Callable] = None
        self._ack_queue: queue.Queue = queue.Queue()
        self._ack_thread: Optional[threading.Thread] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

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
        self.stop_screencast()
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

    # ── Screenshots (existing flow, kept for playback recording) ──────────

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

    # ── CDP Screencast (live view) ─────────────────────────────────────────

    def start_screencast(self, on_frame: Callable[[str, dict], None]) -> bool:
        """
        Start CDP screencast for live browser view.

        on_frame(image_b64, metadata) is called for each JPEG frame pushed by Chrome.
        Returns True if screencast started successfully, False otherwise.

        Implementation notes
        --------------------
        * Frames arrive on Playwright's internal event-loop thread.
        * on_frame must NOT make blocking Playwright calls (risk of deadlock).
        * Page.screencastFrameAck is sent from a dedicated ack thread to avoid
          deadlocking Playwright's event loop.
        """
        if not self._active or not self._page:
            return False
        self._screencast_callback = on_frame
        self._screencast_active = True
        try:
            self._cdp_session = self._page.context.new_cdp_session(self._page)
            # Start ack thread before registering the event handler so the
            # queue consumer is ready when the first frame arrives.
            self._ack_thread = threading.Thread(
                target=self._ack_worker, name="cdp-ack", daemon=True
            )
            self._ack_thread.start()
            self._cdp_session.on("Page.screencastFrame", self._on_screencast_frame)
            self._cdp_session.send("Page.startScreencast", {
                "format":       "jpeg",
                "quality":      70,
                "maxWidth":     self._viewport["width"],
                "maxHeight":    self._viewport["height"],
                "everyNthFrame": 3,   # cap at ~20 fps
            })
            return True
        except Exception:
            self._screencast_active = False
            return False

    def _on_screencast_frame(self, data: dict) -> None:
        """
        CDP event handler — runs on Playwright's internal thread.
        Must not make any synchronous Playwright calls (deadlock risk).
        """
        session_id = data.get("sessionId")
        frame_b64  = data.get("data", "")
        metadata   = data.get("metadata", {})

        # Queue ack — processed by the ack worker thread (non-Playwright thread)
        if session_id is not None and self._screencast_active:
            self._ack_queue.put_nowait(session_id)

        # Forward frame to the callback (also must be non-blocking)
        if self._screencast_callback and frame_b64 and self._screencast_active:
            try:
                self._screencast_callback(frame_b64, metadata)
            except Exception:
                pass

    def _ack_worker(self) -> None:
        """
        Dedicated thread that acknowledges CDP screencast frames.
        Runs outside Playwright's event loop to avoid deadlocks.
        """
        while self._screencast_active or not self._ack_queue.empty():
            try:
                session_id = self._ack_queue.get(timeout=0.5)
            except queue.Empty:
                if not self._screencast_active:
                    break
                continue
            if session_id is None:         # sentinel: stop signal
                break
            try:
                if self._cdp_session and self._screencast_active:
                    self._cdp_session.send(
                        "Page.screencastFrameAck", {"sessionId": session_id}
                    )
            except Exception:
                pass

    def stop_screencast(self) -> None:
        """Stop CDP screencast and clean up the ack thread."""
        if not self._screencast_active:
            return
        self._screencast_active = False
        self._ack_queue.put_nowait(None)   # stop ack worker
        try:
            if self._cdp_session:
                self._cdp_session.send("Page.stopScreencast")
        except Exception:
            pass

    # ── Control Methods (called by ControlLayer) ──────────────────────────

    def click_xy(self, x: float, y: float) -> None:
        """Click at viewport coordinates (x, y)."""
        self._page.mouse.click(x, y)

    def type_text(self, text: str) -> None:
        """Type text using the keyboard."""
        self._page.keyboard.type(text)

    def press_key_str(self, key: str) -> None:
        """Press a named key (e.g. 'Enter', 'Tab', 'Escape', 'ArrowDown')."""
        self._page.keyboard.press(key)

    def navigate_to(self, url: str) -> None:
        """Navigate to a URL and wait for DOM content."""
        self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)

    def scroll_wheel(self, dx: float, dy: float) -> None:
        """Scroll the mouse wheel by (dx, dy) pixels."""
        self._page.mouse.wheel(dx, dy)
