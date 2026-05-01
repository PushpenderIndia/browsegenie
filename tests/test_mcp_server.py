"""Tests for BrowseGenieMCPServer in core/mcp/server.py."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from browsegenie.core.mcp.server import BrowseGenieMCPServer
from browsegenie.core.mcp.exceptions import ConfigurationError


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


class TestBrowseGenieMCPServerInit:
    """Tests for BrowseGenieMCPServer initialisation."""

    def test_server_name_is_browsegenie(self):
        """Test that the server_name attribute is set to 'browsegenie'."""
        server = BrowseGenieMCPServer()
        assert server.server_name == "browsegenie"

    def test_server_version_matches_package(self):
        """Test that server_version matches the installed package version."""
        from browsegenie import __version__
        server = BrowseGenieMCPServer()
        assert server.server_version == __version__

    def test_tool_manager_property_returns_manager(self):
        """Test that the tool_manager property returns a ToolManager instance."""
        from browsegenie.core.mcp.tools import ToolManager
        server = BrowseGenieMCPServer()
        assert isinstance(server.tool_manager, ToolManager)


class TestGetScraper:
    """Tests for the lazy scraper accessor."""

    def test_get_scraper_creates_instance_on_first_call(self):
        """Test that get_scraper() constructs a BrowseGenie instance when none exists."""
        server = BrowseGenieMCPServer()
        with patch("browsegenie.scraper.BrowseGenie") as MockBG:
            MockBG.return_value = MagicMock()
            scraper = server.get_scraper()
            MockBG.assert_called_once()
            assert scraper is server._scraper_instance

    def test_get_scraper_memoizes(self):
        """Test that a second call to get_scraper() returns the same instance without constructing again."""
        server = BrowseGenieMCPServer()
        with patch("browsegenie.scraper.BrowseGenie") as MockBG:
            mock_instance = MagicMock()
            MockBG.return_value = mock_instance
            first = server.get_scraper()
            second = server.get_scraper()
            assert first is second
            MockBG.assert_called_once()

    def test_set_scraper_instance_overrides_lazy(self):
        """Test that set_scraper_instance() replaces the stored scraper."""
        server = BrowseGenieMCPServer()
        custom_scraper = MagicMock()
        server.set_scraper_instance(custom_scraper)
        assert server.get_scraper() is custom_scraper


class TestHandleListTools:
    """Tests for _handle_list_tools."""

    def test_returns_tool_list(self):
        """Test that _handle_list_tools() returns the list of all registered MCP tools."""
        server = BrowseGenieMCPServer()
        tools = _run(server._handle_list_tools())
        assert len(tools) == 5

    def test_exception_raises_configuration_error(self):
        """Test that a ToolManager failure is re-raised as ConfigurationError."""
        import pytest
        server = BrowseGenieMCPServer()
        server._tool_manager.get_all_tools = MagicMock(
            side_effect=Exception("tool manager down")
        )
        with pytest.raises(ConfigurationError, match="tool manager down"):
            _run(server._handle_list_tools())


class TestHandleCallTool:
    """Tests for _handle_call_tool."""

    def test_delegates_to_tool_manager(self):
        """Test that _handle_call_tool calls ToolManager.execute_tool with name and arguments."""
        server = BrowseGenieMCPServer()
        server.set_scraper_instance(MagicMock())
        mock_result = [MagicMock()]
        server._tool_manager.execute_tool = AsyncMock(return_value=mock_result)
        result = _run(server._handle_call_tool("scrape_url", {"url": "https://x.com/p"}))
        server._tool_manager.execute_tool.assert_called_once()
        assert result is mock_result

    def test_exception_returns_error_text_content(self):
        """Test that an unexpected exception during call_tool is returned as an error TextContent."""
        server = BrowseGenieMCPServer()
        server.set_scraper_instance(MagicMock())
        server._tool_manager.execute_tool = AsyncMock(
            side_effect=Exception("unexpected crash")
        )
        result = _run(server._handle_call_tool("scrape_url", {}))
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "error" in data


class TestGetCapabilities:
    """Tests for get_capabilities()."""

    def test_get_capabilities_returns_dict(self):
        """Test that get_capabilities() returns a non-None capabilities object."""
        server = BrowseGenieMCPServer()
        caps = server.get_capabilities()
        assert caps is not None
