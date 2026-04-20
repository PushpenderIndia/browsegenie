"""
Main MCP server implementation for WebAgent.

This module contains the main server class and configuration.
"""

import logging
from typing import Optional

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .tools import ToolManager
from .exceptions import ConfigurationError
from ... import __version__


logger = logging.getLogger(__name__)


class WebAgentMCPServer:
    """
    Main MCP server class for WebAgent.

    This class encapsulates the MCP server functionality and provides
    a clean interface for managing the scraper tools.
    """

    def __init__(self):
        self.server_name = "webagent"
        self.server_version = __version__
        self._server = Server(self.server_name)
        self._tool_manager = ToolManager()
        self._scraper_instance: Optional[object] = None
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP server handlers."""
        self._server.list_tools()(self._handle_list_tools)
        self._server.call_tool()(self._handle_call_tool)

    def get_scraper(self):
        """Get or create a scraper instance."""
        if self._scraper_instance is None:
            from ...scraper import WebAgent
            self._scraper_instance = WebAgent()
        return self._scraper_instance

    def set_scraper_instance(self, scraper):
        """Set a custom scraper instance."""
        self._scraper_instance = scraper

    async def _handle_list_tools(self) -> list[types.Tool]:
        """Handle list_tools request."""
        try:
            return self._tool_manager.get_all_tools()
        except Exception as e:
            logger.exception("Error listing tools")
            raise ConfigurationError(f"Failed to list tools: {str(e)}")

    async def _handle_call_tool(self, name: str, arguments: dict) -> list[types.TextContent]:
        """Handle call_tool request."""
        try:
            scraper = self.get_scraper()
            return await self._tool_manager.execute_tool(name, arguments, scraper)
        except Exception as e:
            logger.exception(f"Error executing tool {name}")
            from .exceptions import ToolExecutionError
            import json
            error = ToolExecutionError(f"Tool execution failed: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps(error.to_dict())
            )]

    async def run(self):
        """Run the MCP server using stdio transport."""
        try:
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                await self._server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=self.server_name,
                        server_version=self.server_version,
                        capabilities=self._server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        )
                    )
                )
        except Exception as e:
            logger.exception("Server runtime error")
            raise ConfigurationError(f"Server failed to run: {str(e)}")

    def get_capabilities(self) -> dict:
        """Get server capabilities."""
        return self._server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={}
        )

    @property
    def tool_manager(self) -> ToolManager:
        """Get the tool manager instance."""
        return self._tool_manager


async def create_and_run_server() -> None:
    """Create and run the MCP server."""
    server = WebAgentMCPServer()
    await server.run()
