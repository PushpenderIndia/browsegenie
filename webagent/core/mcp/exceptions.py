"""
Custom exceptions for the MCP server module.

This module defines custom exception classes used throughout the MCP server implementation.
"""


class MCPServerError(Exception):
    """Base exception class for MCP server errors."""

    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def to_dict(self):
        """Convert the exception to a dictionary for JSON serialization."""
        error_dict = {"error": self.message}
        if self.details:
            error_dict["details"] = self.details
        return error_dict


class ValidationError(MCPServerError):
    """Exception raised when input validation fails."""
    pass


class ToolExecutionError(MCPServerError):
    """Exception raised when tool execution fails."""
    pass


class ConfigurationError(MCPServerError):
    """Exception raised when server configuration is invalid."""
    pass
