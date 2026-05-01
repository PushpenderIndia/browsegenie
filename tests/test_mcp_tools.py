"""Tests for MCP tool definitions and ToolManager in core/mcp/tools.py."""

import asyncio
import json
from unittest.mock import MagicMock, patch

from browsegenie.core.mcp.tools import (
    ClearCacheTool,
    ConfigureScraperTool,
    GetScraperInfoTool,
    ScrapeMultipleURLsTool,
    ScrapeURLTool,
    ToolManager,
)


def _run(coro):
    """Run an async coroutine synchronously for use in non-async tests."""
    return asyncio.run(coro)


def _scraper():
    """Return a mock BrowseGenie scraper instance."""
    s = MagicMock()
    s.scrape_url.return_value = {"title": "Test"}
    s.scrape_multiple_urls.return_value = [{"title": "A"}, {"title": "B"}]
    s.get_model_name.return_value = "gemini-2.5-flash"
    s.get_fields.return_value = ["title"]
    s.get_cache_stats.return_value = {"entries": 3}
    s.clear_cache.return_value = None
    s.cleanup_old_cache.return_value = 2
    return s


# ── ScrapeURLTool ─────────────────────────────────────────────────────────────

class TestScrapeURLTool:
    """Tests for the ScrapeURLTool MCP tool."""

    def setup_method(self):
        """Set up a fresh ScrapeURLTool instance for each test."""
        self.tool = ScrapeURLTool()

    def test_name_is_scrape_url(self):
        """Test that the tool name is 'scrape_url'."""
        assert self.tool.name == "scrape_url"

    def test_description_is_nonempty(self):
        """Test that the tool has a non-empty description."""
        assert len(self.tool.description) > 0

    def test_input_schema_requires_url(self):
        """Test that the input schema declares url as a required field."""
        assert "url" in self.tool.input_schema["required"]

    def test_execute_happy_path(self):
        """Test that execute() returns TextContent with JSON-serialised scrape results."""
        scraper = _scraper()
        result = _run(self.tool.execute({"url": "https://example.com/page"}, scraper))
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data == {"title": "Test"}

    def test_execute_invalid_url_returns_error_content(self):
        """Test that a URL that fails validation returns an error TextContent."""
        scraper = _scraper()
        result = _run(self.tool.execute({"url": "not-a-url"}, scraper))
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "error" in data

    def test_execute_sets_fields_when_provided(self):
        """Test that fields in arguments are forwarded to scraper.set_fields."""
        scraper = _scraper()
        _run(self.tool.execute(
            {"url": "https://example.com/page", "fields": ["title", "price"]}, scraper
        ))
        scraper.set_fields.assert_called_once_with(["title", "price"])

    def test_execute_exception_returns_error_content(self):
        """Test that an unexpected exception during execution is returned as an error TextContent."""
        scraper = _scraper()
        scraper.scrape_url.side_effect = Exception("network error")
        result = _run(self.tool.execute({"url": "https://example.com/page"}, scraper))
        data = json.loads(result[0].text)
        assert "error" in data


# ── ScrapeMultipleURLsTool ────────────────────────────────────────────────────

class TestScrapeMultipleURLsTool:
    """Tests for the ScrapeMultipleURLsTool MCP tool."""

    def setup_method(self):
        """Set up a fresh ScrapeMultipleURLsTool instance for each test."""
        self.tool = ScrapeMultipleURLsTool()

    def test_name_is_scrape_multiple_urls(self):
        """Test that the tool name is 'scrape_multiple_urls'."""
        assert self.tool.name == "scrape_multiple_urls"

    def test_input_schema_requires_urls(self):
        """Test that the input schema declares urls as a required field."""
        assert "urls" in self.tool.input_schema["required"]

    def test_execute_happy_path(self):
        """Test that execute() returns TextContent with a list of scrape results."""
        scraper = _scraper()
        result = _run(self.tool.execute(
            {"urls": ["https://a.com/p", "https://b.com/p"]}, scraper
        ))
        data = json.loads(result[0].text)
        assert isinstance(data, list)

    def test_execute_exception_returns_error(self):
        """Test that an exception from scrape_multiple_urls is returned as an error TextContent."""
        scraper = _scraper()
        scraper.scrape_multiple_urls.side_effect = Exception("boom")
        result = _run(self.tool.execute(
            {"urls": ["https://a.com/p"]}, scraper
        ))
        data = json.loads(result[0].text)
        assert "error" in data


# ── ConfigureScraperTool ──────────────────────────────────────────────────────

class TestConfigureScraperTool:
    """Tests for the ConfigureScraperTool MCP tool."""

    def setup_method(self):
        """Set up a fresh ConfigureScraperTool instance for each test."""
        self.tool = ConfigureScraperTool()

    def test_name_is_configure_scraper(self):
        """Test that the tool name is 'configure_scraper'."""
        assert self.tool.name == "configure_scraper"

    def test_execute_returns_config(self):
        """Test that execute() returns a configuration status dict as TextContent."""
        with patch("browsegenie.scraper.BrowseGenie") as MockBG:
            mock_instance = MagicMock()
            mock_instance.get_model_name.return_value = "gemini-2.5-flash"
            mock_instance.get_fields.return_value = []
            MockBG.return_value = mock_instance
            result = _run(self.tool.execute({}, MagicMock()))
        data = json.loads(result[0].text)
        assert data["status"] == "configured"

    def test_execute_exception_returns_error(self):
        """Test that an exception during configure returns an error TextContent."""
        with patch(
            "browsegenie.scraper.BrowseGenie",
            side_effect=Exception("config fail"),
        ):
            result = _run(self.tool.execute({}, MagicMock()))
        data = json.loads(result[0].text)
        assert "error" in data


# ── GetScraperInfoTool ────────────────────────────────────────────────────────

class TestGetScraperInfoTool:
    """Tests for the GetScraperInfoTool MCP tool."""

    def setup_method(self):
        """Set up a fresh GetScraperInfoTool instance for each test."""
        self.tool = GetScraperInfoTool()

    def test_name_is_get_scraper_info(self):
        """Test that the tool name is 'get_scraper_info'."""
        assert self.tool.name == "get_scraper_info"

    def test_execute_returns_model_and_fields(self):
        """Test that execute() returns model_name and fields from the scraper."""
        scraper = _scraper()
        result = _run(self.tool.execute({}, scraper))
        data = json.loads(result[0].text)
        assert data["model_name"] == "gemini-2.5-flash"
        assert data["fields"] == ["title"]

    def test_execute_exception_returns_error(self):
        """Test that an exception from the scraper is returned as an error TextContent."""
        scraper = MagicMock()
        scraper.get_model_name.side_effect = Exception("info error")
        result = _run(self.tool.execute({}, scraper))
        data = json.loads(result[0].text)
        assert "error" in data


# ── ClearCacheTool ────────────────────────────────────────────────────────────

class TestClearCacheTool:
    """Tests for the ClearCacheTool MCP tool."""

    def setup_method(self):
        """Set up a fresh ClearCacheTool instance for each test."""
        self.tool = ClearCacheTool()

    def test_name_is_clear_cache(self):
        """Test that the tool name is 'clear_cache'."""
        assert self.tool.name == "clear_cache"

    def test_execute_days_zero_calls_clear_cache(self):
        """Test that days_old=0 calls scraper.clear_cache() to remove all entries."""
        scraper = _scraper()
        result = _run(self.tool.execute({"days_old": 0}, scraper))
        scraper.clear_cache.assert_called_once()
        data = json.loads(result[0].text)
        assert data["status"] == "success"

    def test_execute_days_positive_calls_cleanup_old_cache(self):
        """Test that days_old>0 calls scraper.cleanup_old_cache() with the given days."""
        scraper = _scraper()
        result = _run(self.tool.execute({"days_old": 7}, scraper))
        scraper.cleanup_old_cache.assert_called_once_with(7)
        data = json.loads(result[0].text)
        assert data["status"] == "success"

    def test_execute_exception_returns_error(self):
        """Test that an exception during cache clearing returns an error TextContent."""
        scraper = _scraper()
        scraper.clear_cache.side_effect = Exception("db locked")
        result = _run(self.tool.execute({"days_old": 0}, scraper))
        data = json.loads(result[0].text)
        assert "error" in data


# ── ToolManager ───────────────────────────────────────────────────────────────

class TestToolManager:
    """Tests for the ToolManager registry class."""

    def setup_method(self):
        """Create a fresh ToolManager for each test."""
        self.manager = ToolManager()

    def test_get_all_tools_returns_five_tools(self):
        """Test that get_all_tools() returns all five registered MCP Tool objects."""
        tools = self.manager.get_all_tools()
        assert len(tools) == 5

    def test_get_tool_by_name(self):
        """Test that get_tool() returns the correct tool instance by name."""
        tool = self.manager.get_tool("scrape_url")
        assert tool is not None
        assert tool.name == "scrape_url"

    def test_get_tool_unknown_returns_none(self):
        """Test that get_tool() returns None for an unregistered tool name."""
        assert self.manager.get_tool("nonexistent") is None

    def test_execute_tool_unknown_returns_error_content(self):
        """Test that execute_tool() with an unknown name returns an error TextContent."""
        result = _run(self.manager.execute_tool("ghost_tool", {}, MagicMock()))
        data = json.loads(result[0].text)
        assert "error" in data

    def test_to_mcp_tool_shape(self):
        """Test that each tool converts to an MCP Tool with name, description, and inputSchema."""
        for mcp_tool in self.manager.get_all_tools():
            assert mcp_tool.name
            assert mcp_tool.description
            assert mcp_tool.inputSchema
