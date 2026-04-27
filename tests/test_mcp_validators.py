"""Tests for MCP validators and exceptions."""

import pytest

from browsegenie.core.mcp.exceptions import (
    ConfigurationError,
    MCPServerError,
    ToolExecutionError,
    ValidationError,
)
from browsegenie.core.mcp.validators import FieldValidator, FormatValidator, URLValidator


# ── Exceptions ────────────────────────────────────────────────────────────────

class TestMCPServerError:
    """Test cases for the MCPServerError base exception class."""

    def test_basic_message(self):
        """Test that MCPServerError stores the message and has no details by default."""
        err = MCPServerError("something broke")
        assert str(err) == "something broke"
        assert err.message == "something broke"
        assert err.details is None

    def test_with_details(self):
        """Test that optional details are stored when provided."""
        err = MCPServerError("broke", details="full stack trace here")
        assert err.details == "full stack trace here"

    def test_to_dict_no_details(self):
        """Test that to_dict returns only the error key when no details are set."""
        err = MCPServerError("error occurred")
        d = err.to_dict()
        assert d == {"error": "error occurred"}
        assert "details" not in d

    def test_to_dict_with_details(self):
        """Test that to_dict includes the details key when details are set."""
        err = MCPServerError("error", details="more info")
        d = err.to_dict()
        assert d["error"] == "error"
        assert d["details"] == "more info"

    def test_is_exception(self):
        """Test that MCPServerError is a subclass of Exception."""
        err = MCPServerError("test")
        assert isinstance(err, Exception)


class TestValidationError:
    """Test cases for the ValidationError exception class."""

    def test_is_mcp_server_error(self):
        """Test that ValidationError inherits from MCPServerError."""
        err = ValidationError("bad input")
        assert isinstance(err, MCPServerError)
        assert isinstance(err, ValidationError)

    def test_raised_and_caught(self):
        """Test that ValidationError can be raised and caught normally."""
        with pytest.raises(ValidationError):
            raise ValidationError("invalid url")


class TestToolExecutionError:
    """Test cases for the ToolExecutionError exception class."""

    def test_is_mcp_server_error(self):
        """Test that ToolExecutionError inherits from MCPServerError."""
        err = ToolExecutionError("tool failed")
        assert isinstance(err, MCPServerError)

    def test_with_details(self):
        """Test that ToolExecutionError stores details correctly."""
        err = ToolExecutionError("failed", details="timeout after 30s")
        assert err.details == "timeout after 30s"


class TestConfigurationError:
    """Test cases for the ConfigurationError exception class."""

    def test_is_mcp_server_error(self):
        """Test that ConfigurationError inherits from MCPServerError."""
        err = ConfigurationError("bad config")
        assert isinstance(err, MCPServerError)


# ── URLValidator ──────────────────────────────────────────────────────────────

class TestURLValidator:
    """Test cases for the URLValidator class."""

    def test_valid_http_url(self):
        """Test that a standard http URL passes validation."""
        assert URLValidator.validate_url("http://example.com") is True

    def test_valid_https_url(self):
        """Test that an https URL with path and query string passes validation."""
        assert URLValidator.validate_url("https://example.com/path?q=1") is True

    def test_empty_url_raises(self):
        """Test that an empty string raises ValidationError with a 'required' message."""
        with pytest.raises(ValidationError, match="required"):
            URLValidator.validate_url("")

    def test_non_string_raises(self):
        """Test that a non-string input raises ValidationError."""
        with pytest.raises(ValidationError, match="string"):
            URLValidator.validate_url(123)  # type: ignore[arg-type]

    def test_no_scheme_raises(self):
        """Test that a URL without a scheme raises ValidationError."""
        with pytest.raises(ValidationError):
            URLValidator.validate_url("example.com/page")

    def test_ftp_scheme_raises(self):
        """Test that a non-http/https scheme raises ValidationError."""
        with pytest.raises(ValidationError, match="http or https"):
            URLValidator.validate_url("ftp://example.com")

    def test_url_with_path_and_query(self):
        """Test that a complex URL with path and multiple query parameters is valid."""
        assert URLValidator.validate_url("https://api.example.com/v1/search?q=test&page=2") is True

    def test_validate_urls_list(self):
        """Test that a list of valid URLs passes batch validation."""
        urls = ["https://a.com", "http://b.org"]
        assert URLValidator.validate_urls(urls) is True

    def test_validate_urls_empty_list_raises(self):
        """Test that an empty URL list raises ValidationError."""
        with pytest.raises(ValidationError, match="required"):
            URLValidator.validate_urls([])

    def test_validate_urls_not_list_raises(self):
        """Test that passing a non-list to validate_urls raises ValidationError."""
        with pytest.raises(ValidationError, match="list"):
            URLValidator.validate_urls("https://example.com")  # type: ignore[arg-type]

    def test_validate_urls_with_invalid_raises(self):
        """Test that a list containing an invalid URL raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid"):
            URLValidator.validate_urls(["https://valid.com", "not-a-url"])


# ── FieldValidator ────────────────────────────────────────────────────────────

class TestFieldValidator:
    """Test cases for the FieldValidator class."""

    def test_valid_fields(self):
        """Test that a list of unique string field names passes validation."""
        assert FieldValidator.validate_fields(["name", "price", "rating"]) is True

    def test_none_fields_ok(self):
        """Test that None is accepted as a valid (absent) fields argument."""
        assert FieldValidator.validate_fields(None) is True  # type: ignore[arg-type]

    def test_empty_list_ok(self):
        """Test that an empty fields list is accepted."""
        assert FieldValidator.validate_fields([]) is True

    def test_not_list_raises(self):
        """Test that passing a non-list raises ValidationError."""
        with pytest.raises(ValidationError, match="list"):
            FieldValidator.validate_fields("price")  # type: ignore[arg-type]

    def test_non_string_field_raises(self):
        """Test that a list containing a non-string element raises ValidationError."""
        with pytest.raises(ValidationError, match="strings"):
            FieldValidator.validate_fields(["price", 123])  # type: ignore[list-item]

    def test_duplicate_fields_raises(self):
        """Test that duplicate field names raise a ValidationError."""
        with pytest.raises(ValidationError, match="Duplicate"):
            FieldValidator.validate_fields(["name", "price", "name"])

    def test_single_field(self):
        """Test that a single-element fields list passes validation."""
        assert FieldValidator.validate_fields(["title"]) is True


# ── FormatValidator ───────────────────────────────────────────────────────────

class TestFormatValidator:
    """Test cases for the FormatValidator class."""

    def test_json_valid(self):
        """Test that 'json' is an accepted output format."""
        assert FormatValidator.validate_format("json") is True

    def test_csv_valid(self):
        """Test that 'csv' is an accepted output format."""
        assert FormatValidator.validate_format("csv") is True

    def test_invalid_format_raises(self):
        """Test that an unsupported format like 'xml' raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid format"):
            FormatValidator.validate_format("xml")

    def test_empty_string_raises(self):
        """Test that an empty string raises ValidationError."""
        with pytest.raises(ValidationError):
            FormatValidator.validate_format("")

    def test_uppercase_invalid(self):
        """Test that format validation is case-sensitive (uppercase 'JSON' is rejected)."""
        with pytest.raises(ValidationError):
            FormatValidator.validate_format("JSON")
