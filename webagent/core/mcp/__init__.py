"""
MCP (Model Context Protocol) module for WebAgent

This module provides a clean, modular MCP server implementation using OOP principles.
The MCP server exposes the WebAgent functionality as tools that can be used by AI models.
"""

from .server import WebAgentMCPServer
from .tools import ToolManager
from .validators import URLValidator
from .exceptions import MCPServerError, ValidationError

__all__ = [
    "WebAgentMCPServer",
    "ToolManager",
    "URLValidator",
    "MCPServerError",
    "ValidationError"
]
