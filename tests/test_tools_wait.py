"""Tests for browser-agent wait tools: wait_for_element, wait_for_load, wait_for_url."""

from unittest.mock import MagicMock

from browsegenie.core.browser_agent.tools.wait import (
    wait_for_element,
    wait_for_load,
    wait_for_url,
)


def _page(url="https://example.com"):
    """Return a mock Playwright Page with preset url."""
    page = MagicMock()
    page.url = url
    return page


class TestWaitForElement:
    """Tests for the wait_for_element() tool."""

    def test_element_found(self):
        """Test that wait_for_element returns found=True when selector appears."""
        page = _page()
        result = wait_for_element(page, "#submit")
        assert result["found"] is True
        assert result["selector"] == "#submit"
        assert result["state"] == "visible"

    def test_element_not_found_on_timeout(self):
        """Test that wait_for_element returns found=False when wait times out."""
        page = _page()
        page.wait_for_selector.side_effect = Exception("timeout")
        result = wait_for_element(page, "#missing")
        assert result["found"] is False
        assert result["selector"] == "#missing"

    def test_custom_state_forwarded(self):
        """Test that a custom state value is forwarded to page.wait_for_selector."""
        page = _page()
        wait_for_element(page, "button", state="attached", timeout=5000)
        page.wait_for_selector.assert_called_once_with(
            "button", state="attached", timeout=5000
        )


class TestWaitForLoad:
    """Tests for the wait_for_load() tool."""

    def test_loaded_success(self):
        """Test that wait_for_load returns loaded=True on success."""
        page = _page(url="https://loaded.com")
        result = wait_for_load(page)
        assert result["loaded"] is True
        assert result["url"] == "https://loaded.com"

    def test_loaded_failure(self):
        """Test that wait_for_load returns loaded=False when the wait times out."""
        page = _page()
        page.wait_for_load_state.side_effect = Exception("timeout")
        result = wait_for_load(page)
        assert result["loaded"] is False

    def test_default_state_is_domcontentloaded(self):
        """Test that the default load state is domcontentloaded."""
        page = _page()
        wait_for_load(page)
        page.wait_for_load_state.assert_called_once_with(
            "domcontentloaded", timeout=10000
        )


class TestWaitForUrl:
    """Tests for the wait_for_url() tool."""

    def test_matched_success(self):
        """Test that wait_for_url returns matched=True when the URL matches."""
        page = _page(url="https://dashboard.com")
        result = wait_for_url(page, "dashboard")
        assert result["matched"] is True
        assert result["url"] == "https://dashboard.com"

    def test_matched_failure(self):
        """Test that wait_for_url returns matched=False when the URL never matches."""
        page = _page()
        page.wait_for_url.side_effect = Exception("timeout")
        result = wait_for_url(page, "never-appears")
        assert result["matched"] is False

    def test_url_pattern_forwarded(self):
        """Test that the url_pattern argument is passed directly to page.wait_for_url."""
        page = _page()
        wait_for_url(page, "**/dashboard*", timeout=3000)
        page.wait_for_url.assert_called_once_with("**/dashboard*", timeout=3000)
