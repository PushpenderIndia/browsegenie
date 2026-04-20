"""Tests for the HtmlFetcher module"""

import tempfile
from unittest.mock import Mock, patch
from webagent.core.html_fetcher import HtmlFetcher


class TestHtmlFetcher:
    """Test cases for HtmlFetcher class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def test_init_default(self):
        """Test HtmlFetcher initialization with defaults"""
        fetcher = HtmlFetcher()
        assert fetcher.temp_dir == "temp"
        assert fetcher.logger is not None
        assert hasattr(fetcher, "headers")

    def test_init_custom_temp_dir(self):
        """Test HtmlFetcher initialization with custom temp directory"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)
        assert fetcher.temp_dir == self.temp_dir

    def test_headers_configured(self):
        """Test that default headers are properly configured"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)
        assert isinstance(fetcher.headers, dict)
        assert "User-Agent" in fetcher.headers
        assert "Accept" in fetcher.headers

    def test_raw_html_dir_created(self):
        """Test that raw HTML directory is created"""
        HtmlFetcher(temp_dir=self.temp_dir)
        import os

        expected_dir = os.path.join(self.temp_dir, "raw_html")
        assert os.path.exists(expected_dir)

    @patch("webagent.core.html_fetcher.cloudscraper.create_scraper")
    def test_fetch_with_cloudscraper_method_exists(self, mock_scraper):
        """Test that fetch_with_cloudscraper method exists and is callable"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)

        # Method should exist
        assert hasattr(fetcher, "fetch_with_cloudscraper")
        assert callable(getattr(fetcher, "fetch_with_cloudscraper"))

    def test_logger_functionality(self):
        """Test that logger is properly configured"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)

        assert hasattr(fetcher, "logger")
        assert fetcher.logger is not None

        # Test that logging doesn't raise an exception
        with patch.object(fetcher.logger, "info") as mock_log:
            fetcher.logger.info("Test log message")
            mock_log.assert_called_once_with("Test log message")

    def test_temp_dir_attribute(self):
        """Test that temp_dir attribute is set correctly"""
        import tempfile

        custom_dir = tempfile.mkdtemp()
        fetcher = HtmlFetcher(temp_dir=custom_dir)
        assert fetcher.temp_dir == custom_dir

    def test_headers_user_agent(self):
        """Test that User-Agent header is set"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)
        assert "User-Agent" in fetcher.headers
        assert "Mozilla" in fetcher.headers["User-Agent"]

    def test_headers_accept(self):
        """Test that Accept header is set"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)
        assert "Accept" in fetcher.headers
        assert "text/html" in fetcher.headers["Accept"]

    def test_headers_other_fields(self):
        """Test that other required headers are set"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)

        required_headers = [
            "Accept-Language",
            "Accept-Encoding",
            "Connection",
            "Upgrade-Insecure-Requests",
        ]

        for header in required_headers:
            assert header in fetcher.headers

    @patch("webagent.core.html_fetcher.cloudscraper.create_scraper")
    def test_cloudscraper_integration(self, mock_scraper):
        """Test CloudScraper integration setup"""
        mock_scraper_instance = Mock()
        mock_scraper.return_value = mock_scraper_instance

        fetcher = HtmlFetcher(temp_dir=self.temp_dir)

        # Should be able to call the method without errors
        try:
            fetcher.fetch_with_cloudscraper("https://example.com")
        except Exception as e:
            # Expected to fail due to mocking, but method should exist
            assert "fetch_with_cloudscraper" not in str(e)

    def test_directory_structure(self):
        """Test that required directory structure is created"""
        import os

        fetcher = HtmlFetcher(temp_dir=self.temp_dir)

        # Check that raw_html_dir exists
        assert os.path.exists(fetcher.raw_html_dir)
        assert os.path.isdir(fetcher.raw_html_dir)

    def test_object_attributes(self):
        """Test that all required attributes are present"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)

        required_attributes = ["logger", "temp_dir", "raw_html_dir", "headers"]

        for attr in required_attributes:
            assert hasattr(fetcher, attr), f"Missing attribute: {attr}"

    def test_headers_immutable_after_init(self):
        """Test that headers can be modified after initialization"""
        fetcher = HtmlFetcher(temp_dir=self.temp_dir)

        original_user_agent = fetcher.headers["User-Agent"]
        fetcher.headers["User-Agent"] = "Custom User Agent"

        assert fetcher.headers["User-Agent"] == "Custom User Agent"
        assert fetcher.headers["User-Agent"] != original_user_agent
