"""Tests for the main WebAgent class"""

import os
import tempfile
from unittest.mock import patch
from webagent import WebAgent


class TestWebAgent:
    """Test cases for WebAgent class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

    def test_init_default_params(self):
        """Test WebAgent initialization with default parameters"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent()
            assert scraper.temp_dir == "temp"
            assert scraper.output_dir == "output"
            assert hasattr(scraper, "extraction_fields")
            assert scraper.logger is not None

    def test_init_custom_params(self):
        """Test WebAgent initialization with custom parameters"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(
                api_key="test_key",
                temp_dir=self.temp_dir,
                output_dir=self.output_dir,
                model_name="gemini-2.5-flash",
            )
            assert scraper.temp_dir == self.temp_dir
            assert scraper.output_dir == self.output_dir
            assert scraper.api_key == "test_key"

    def test_logging_setup(self):
        """Test that logging is properly set up"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)
            assert hasattr(scraper, "logger")
            assert scraper.logger is not None

    def test_modules_initialized(self):
        """Test that all required modules are initialized"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(
                temp_dir=self.temp_dir, output_dir=self.output_dir
            )

            required_modules = ["fetcher", "cleaner", "extractor"]
            for module in required_modules:
                assert hasattr(scraper, module), f"Missing module: {module}"

    def test_directories_created(self):
        """Test that required directories are created"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch("os.makedirs") as mock_makedirs:
                WebAgent(
                    temp_dir=self.temp_dir, output_dir=self.output_dir
                )
                # makedirs should have been called for both directories
                assert mock_makedirs.call_count >= 2

    def test_default_extraction_fields(self):
        """Test that default extraction fields are set"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)
            assert hasattr(scraper, "extraction_fields")
            assert isinstance(scraper.extraction_fields, list)
            assert len(scraper.extraction_fields) > 0

    def test_model_name_setting(self):
        """Test model name setting and detection"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            # Test with explicit model name
            scraper = WebAgent(
                temp_dir=self.temp_dir, model_name="gemini-2.5-flash"
            )
            assert scraper.model_name == "gemini-2.5-flash"

    def test_api_key_setting(self):
        """Test API key setting"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env_key"}):
            # Test with explicit API key
            scraper = WebAgent(
                api_key="explicit_key", temp_dir=self.temp_dir
            )
            assert scraper.api_key == "explicit_key"

    def test_fetcher_initialization(self):
        """Test that HtmlFetcher is properly initialized"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)
            assert hasattr(scraper, "fetcher")
            assert scraper.fetcher.temp_dir == self.temp_dir

    def test_cleaner_initialization(self):
        """Test that HtmlCleaner is properly initialized"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)
            assert hasattr(scraper, "cleaner")
            assert scraper.cleaner.temp_dir == self.temp_dir

    def test_extractor_initialization(self):
        """Test that DataExtractor is properly initialized"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(
                api_key="test_key",
                temp_dir=self.temp_dir,
                output_dir=self.output_dir,
            )
            assert hasattr(scraper, "extractor")

    def test_setup_logging_method(self):
        """Test that setup_logging method exists and works"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)
            assert hasattr(scraper, "setup_logging")
            assert callable(getattr(scraper, "setup_logging"))

    def test_detect_default_model_method(self):
        """Test that _detect_default_model method exists"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)
            assert hasattr(scraper, "_detect_default_model")

            # Test method functionality
            default_model = scraper._detect_default_model("test_key")
            assert isinstance(default_model, str)
            assert len(default_model) > 0

    def test_extraction_fields_default_values(self):
        """Test that default extraction fields contain expected values"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)

            expected_fields = [
                "company_name",
                "job_title",
                "apply_link",
                "salary_range",
            ]
            for field in expected_fields:
                assert field in scraper.extraction_fields

    def test_object_attributes_present(self):
        """Test that all required object attributes are present"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(
                api_key="test_key",
                temp_dir=self.temp_dir,
                output_dir=self.output_dir,
            )

            required_attributes = [
                "temp_dir",
                "output_dir",
                "api_key",
                "model_name",
                "extraction_fields",
                "logger",
                "fetcher",
                "cleaner",
                "extractor",
            ]

            for attr in required_attributes:
                assert hasattr(scraper, attr), f"Missing attribute: {attr}"

    def test_logging_level_setting(self):
        """Test that logging level can be set"""
        import logging

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(
                temp_dir=self.temp_dir, log_level=logging.DEBUG
            )
            # Should not raise an exception
            assert scraper is not None


class TestWebAgentMethods:
    """Test cases for WebAgent methods"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

    def test_methods_exist(self):
        """Test that expected methods exist"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)

            expected_methods = ["setup_logging", "_detect_default_model"]

            for method in expected_methods:
                assert hasattr(scraper, method), f"Missing method: {method}"
                assert callable(
                    getattr(scraper, method)
                ), f"Method {method} is not callable"

    def test_string_representation(self):
        """Test string representation of WebAgent"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            scraper = WebAgent(temp_dir=self.temp_dir)
            str_repr = str(scraper)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0
