"""Tests for browser-agent navigation tools: navigate, go_back, go_forward, reload."""

from unittest.mock import MagicMock

from browsegenie.core.browser_agent.tools.navigation import (
    go_back,
    go_forward,
    navigate,
    reload,
)


def _page(url="https://example.com", title="Example"):
    """Return a mock Playwright Page with preset url and title."""
    page = MagicMock()
    page.url = url
    page.title.return_value = title
    return page


class TestNavigate:
    """Tests for the navigate() tool."""

    def test_navigate_calls_goto(self):
        """Test that navigate calls page.goto with the given URL."""
        page = _page()
        navigate(page, "https://example.com")
        page.goto.assert_called_once_with(
            "https://example.com", wait_until="load", timeout=30000
        )

    def test_navigate_returns_url_and_title(self):
        """Test that navigate returns a dict with url and title keys."""
        page = _page(url="https://example.com", title="Example Domain")
        result = navigate(page, "https://example.com")
        assert result["url"] == "https://example.com"
        assert result["title"] == "Example Domain"

    def test_navigate_networkidle_exception_swallowed(self):
        """Test that a networkidle timeout is silently ignored and navigate still succeeds."""
        page = _page()
        page.wait_for_load_state.side_effect = Exception("networkidle timeout")
        result = navigate(page, "https://example.com")
        assert "url" in result

    def test_navigate_calls_wait_for_load_state(self):
        """Test that navigate attempts to wait for networkidle after goto."""
        page = _page()
        navigate(page, "https://example.com")
        page.wait_for_load_state.assert_called_once_with("networkidle", timeout=5000)


class TestGoBack:
    """Tests for the go_back() tool."""

    def test_go_back_calls_page_go_back(self):
        """Test that go_back delegates to page.go_back with domcontentloaded."""
        page = _page()
        go_back(page)
        page.go_back.assert_called_once_with(
            wait_until="domcontentloaded", timeout=10000
        )

    def test_go_back_returns_url(self):
        """Test that go_back returns a dict containing the current url."""
        page = _page(url="https://previous.com")
        result = go_back(page)
        assert result["url"] == "https://previous.com"


class TestGoForward:
    """Tests for the go_forward() tool."""

    def test_go_forward_calls_page_go_forward(self):
        """Test that go_forward delegates to page.go_forward with domcontentloaded."""
        page = _page()
        go_forward(page)
        page.go_forward.assert_called_once_with(
            wait_until="domcontentloaded", timeout=10000
        )

    def test_go_forward_returns_url(self):
        """Test that go_forward returns a dict containing the current url."""
        page = _page(url="https://next.com")
        result = go_forward(page)
        assert result["url"] == "https://next.com"


class TestReload:
    """Tests for the reload() tool."""

    def test_reload_calls_page_reload(self):
        """Test that reload delegates to page.reload with domcontentloaded."""
        page = _page()
        reload(page)
        page.reload.assert_called_once_with(
            wait_until="domcontentloaded", timeout=15000
        )

    def test_reload_returns_url_and_title(self):
        """Test that reload returns a dict with url and title keys."""
        page = _page(url="https://example.com", title="Reloaded Page")
        result = reload(page)
        assert result["url"] == "https://example.com"
        assert result["title"] == "Reloaded Page"
