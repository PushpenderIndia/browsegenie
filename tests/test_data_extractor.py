"""Tests for the DataExtractor module"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch


class TestDataExtractor:
    """Test cases for DataExtractor class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

    @patch("webagent.core.data_extractor.genai.Client")
    def test_init_with_api_key(self, mock_client):
        """Test DataExtractor initialization with API key"""
        from webagent.core.data_extractor import DataExtractor

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance

        extractor = DataExtractor(
            api_key="test_key",
            temp_dir=self.temp_dir,
            output_dir=self.output_dir,
            model_name="gemini-2.5-flash",
        )

        assert extractor.api_key == "test_key"
        assert extractor.model_name == "gemini-2.5-flash"
        assert extractor.temp_dir == self.temp_dir
        mock_client.assert_called_once_with(api_key="test_key")

    @patch("webagent.core.data_extractor.genai.Client")
    def test_init_with_env_var(self, mock_client):
        """Test DataExtractor initialization with env variable"""
        from webagent.core.data_extractor import DataExtractor

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance

        with patch.dict(os.environ, {"GEMINI_API_KEY": "env_key"}):
            extractor = DataExtractor(
                temp_dir=self.temp_dir, output_dir=self.output_dir
            )
            assert extractor.model_name == "gemini-2.5-flash"
            mock_client.assert_called_once_with(api_key="env_key")

    def test_init_no_api_key(self):
        """Test DataExtractor initialization without API key"""
        from webagent.core.data_extractor import DataExtractor

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="Gemini API key not provided"
            ):
                DataExtractor(
                    temp_dir=self.temp_dir, output_dir=self.output_dir
                )

    @patch("webagent.core.data_extractor.LITELLM_AVAILABLE", True)
    def test_init_litellm_model(self):
        """Test DataExtractor initialization with LiteLLM model"""
        from webagent.core.data_extractor import DataExtractor

        extractor = DataExtractor(
            api_key="test_key",
            temp_dir=self.temp_dir,
            output_dir=self.output_dir,
            model_name="gpt-4",
        )
        assert extractor.model_name == "gpt-4"
        assert extractor.use_litellm is True

    def test_directories_created(self):
        """Test that required directories are created"""
        from webagent.core.data_extractor import DataExtractor

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch("webagent.core.data_extractor.genai.Client"):
                extractor = DataExtractor(
                    temp_dir=self.temp_dir, output_dir=self.output_dir
                )

                assert os.path.exists(extractor.extraction_codes_dir)
                assert os.path.exists(self.output_dir)

    def test_enable_cache_setting(self):
        """Test cache enable/disable setting"""
        from webagent.core.data_extractor import DataExtractor

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch("webagent.core.data_extractor.genai.Client"):
                # Test with cache enabled
                extractor = DataExtractor(
                    temp_dir=self.temp_dir,
                    output_dir=self.output_dir,
                    enable_cache=True,
                )
                assert extractor.enable_cache is True
                assert extractor.code_cache is not None

                # Test with cache disabled
                extractor_no_cache = DataExtractor(
                    temp_dir=self.temp_dir,
                    output_dir=self.output_dir,
                    enable_cache=False,
                )
                assert extractor_no_cache.enable_cache is False
                assert extractor_no_cache.code_cache is None

    def test_default_model_name(self):
        """Test default model name setting"""
        from webagent.core.data_extractor import DataExtractor

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch("webagent.core.data_extractor.genai.Client"):
                extractor = DataExtractor(
                    temp_dir=self.temp_dir, output_dir=self.output_dir
                )
                assert extractor.model_name == "gemini-2.5-flash"

    def test_extraction_history_initialized(self):
        """Test that extraction history is initialized"""
        from webagent.core.data_extractor import DataExtractor

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch("webagent.core.data_extractor.genai.Client"):
                extractor = DataExtractor(
                    temp_dir=self.temp_dir, output_dir=self.output_dir
                )
                assert hasattr(extractor, "extraction_history")
                assert isinstance(extractor.extraction_history, list)

    def test_logger_configured(self):
        """Test that logger is properly configured"""
        from webagent.core.data_extractor import DataExtractor

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch("webagent.core.data_extractor.genai.Client"):
                extractor = DataExtractor(
                    temp_dir=self.temp_dir, output_dir=self.output_dir
                )
                assert hasattr(extractor, "logger")
                assert extractor.logger is not None
