"""Extra tests for HtmlFetcher: SPA path, short-content fallback, dual-failure, selenium errors."""

import tempfile
from unittest.mock import MagicMock, patch

from browsegenie.core.html_fetcher import HtmlFetcher


def _fetcher():
    """Return an HtmlFetcher using an isolated temp directory."""
    return HtmlFetcher(temp_dir=tempfile.mkdtemp())


class TestFetchWithCloudscraper:
    """Tests for fetch_with_cloudscraper() behaviour."""

    def test_happy_path_returns_html(self):
        """Test that fetch_with_cloudscraper returns the response text on success."""
        fetcher = _fetcher()
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Hello</body></html>"
        with patch("browsegenie.core.html_fetcher.cloudscraper.create_scraper") as mock_cs:
            mock_cs.return_value.get.return_value = mock_resp
            result = fetcher.fetch_with_cloudscraper("https://example.com")
        assert result == "<html><body>Hello</body></html>"

    def test_exception_returns_none(self):
        """Test that fetch_with_cloudscraper returns None when the request raises an exception."""
        fetcher = _fetcher()
        with patch("browsegenie.core.html_fetcher.cloudscraper.create_scraper") as mock_cs:
            mock_cs.return_value.get.side_effect = Exception("connection refused")
            result = fetcher.fetch_with_cloudscraper("https://example.com")
        assert result is None


class TestFetchWithSelenium:
    """Tests for fetch_with_selenium() error paths."""

    def _chrome_patch(self, driver=None, exception=None):
        """Return a context manager that patches webdriver.Chrome."""
        if exception:
            return patch(
                "browsegenie.core.html_fetcher.webdriver.Chrome",
                side_effect=exception,
            )
        mock_driver = driver or MagicMock()
        return patch(
            "browsegenie.core.html_fetcher.webdriver.Chrome",
            return_value=mock_driver,
        )

    def test_timeout_exception_returns_none(self):
        """Test that a Selenium TimeoutException causes fetch_with_selenium to return None."""
        from selenium.common.exceptions import TimeoutException
        fetcher = _fetcher()
        mock_driver = MagicMock()
        mock_driver.get.return_value = None
        mock_wait = MagicMock()
        mock_wait.until.side_effect = TimeoutException("timed out")
        with self._chrome_patch(driver=mock_driver), \
             patch("browsegenie.core.html_fetcher.WebDriverWait", return_value=mock_wait), \
             patch("browsegenie.core.html_fetcher.time.sleep"):
            result = fetcher.fetch_with_selenium("https://slow.example.com")
        assert result is None

    def test_webdriver_exception_returns_none(self):
        """Test that a WebDriverException causes fetch_with_selenium to return None."""
        from selenium.common.exceptions import WebDriverException
        fetcher = _fetcher()
        with self._chrome_patch(exception=WebDriverException("chromedriver missing")):
            result = fetcher.fetch_with_selenium("https://example.com")
        assert result is None


class TestFetchHtml:
    """Tests for the high-level fetch_html() routing logic."""

    def test_static_page_returns_cloudscraper_html(self):
        """Test that a normal static page is returned directly from cloudscraper."""
        fetcher = _fetcher()
        good_html = "<html><body>" + "x" * 200 + "</body></html>"
        fetcher.fetch_with_cloudscraper = MagicMock(return_value=good_html)
        fetcher.detector.detect = MagicMock(return_value={"is_spa": False})
        fetcher._save_raw_html = MagicMock()
        result = fetcher.fetch_html("https://example.com")
        assert result == good_html
        fetcher.fetch_with_cloudscraper.assert_called_once()

    def test_spa_detected_falls_through_to_selenium(self):
        """Test that a detected SPA skips the cloudscraper result and falls through to Selenium."""
        fetcher = _fetcher()
        good_html = "<html><body>" + "x" * 200 + "</body></html>"
        selenium_html = "<html><body>Rendered SPA " + "y" * 200 + "</body></html>"
        fetcher.fetch_with_cloudscraper = MagicMock(return_value=good_html)
        fetcher.detector.detect = MagicMock(
            return_value={"is_spa": True, "framework": "Next.js", "reason": "next-data"}
        )
        fetcher.fetch_with_selenium = MagicMock(return_value=selenium_html)
        fetcher._save_raw_html = MagicMock()
        result = fetcher.fetch_html("https://spa.example.com")
        assert result == selenium_html

    def test_short_cloudscraper_response_falls_through_to_selenium(self):
        """Test that a cloudscraper response shorter than 100 chars triggers Selenium fallback."""
        fetcher = _fetcher()
        fetcher.fetch_with_cloudscraper = MagicMock(return_value="<html></html>")
        selenium_html = "<html><body>" + "z" * 200 + "</body></html>"
        fetcher.fetch_with_selenium = MagicMock(return_value=selenium_html)
        fetcher._save_raw_html = MagicMock()
        result = fetcher.fetch_html("https://example.com")
        assert result == selenium_html

    def test_both_methods_fail_raises_exception(self):
        """Test that fetch_html raises an exception when both cloudscraper and Selenium fail."""
        import pytest
        fetcher = _fetcher()
        fetcher.fetch_with_cloudscraper = MagicMock(return_value=None)
        fetcher.fetch_with_selenium = MagicMock(return_value=None)
        with pytest.raises(Exception, match="Failed to fetch HTML"):
            fetcher.fetch_html("https://unreachable.example.com")

    def test_cloudscraper_none_fallback_to_selenium(self):
        """Test that a None result from cloudscraper triggers the Selenium fallback."""
        fetcher = _fetcher()
        selenium_html = "<html><body>" + "a" * 200 + "</body></html>"
        fetcher.fetch_with_cloudscraper = MagicMock(return_value=None)
        fetcher.fetch_with_selenium = MagicMock(return_value=selenium_html)
        fetcher._save_raw_html = MagicMock()
        result = fetcher.fetch_html("https://example.com")
        assert result == selenium_html
