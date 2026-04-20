"""
Tool definitions and management for the MCP server.

This module contains tool definitions and the ToolManager class for handling MCP tools.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

import mcp.types as types
from .exceptions import ToolExecutionError, ValidationError
from .validators import URLValidator, FieldValidator, FormatValidator


logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for MCP tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema."""
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any], scraper) -> List[types.TextContent]:
        """Execute the tool with given arguments."""
        pass

    def to_mcp_tool(self) -> types.Tool:
        """Convert to MCP Tool type."""
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )


class ScrapeURLTool(BaseTool):
    """Tool for scraping a single URL."""

    @property
    def name(self) -> str:
        return "scrape_url"

    @property
    def description(self) -> str:
        return "Scrape a single URL and extract structured data using AI"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to scrape"
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of fields to extract (e.g., ['title', 'price', 'description'])",
                    "default": []
                },
                "api_key": {
                    "type": "string",
                    "description": "AI provider API key (optional if set in environment)",
                    "default": None
                },
                "model_name": {
                    "type": "string",
                    "description": "AI model to use (e.g., 'gemini-2.5-flash', 'gpt-4', 'claude-3-haiku-20240307')",
                    "default": None
                },
                "format": {
                    "type": "string",
                    "enum": ["json", "csv"],
                    "description": "Output format",
                    "default": "json"
                },
                "save_to_file": {
                    "type": "boolean",
                    "description": "Whether to save output to file",
                    "default": False
                }
            },
            "required": ["url"]
        }

    async def execute(self, arguments: Dict[str, Any], scraper) -> List[types.TextContent]:
        """Execute the scrape_url tool."""
        try:
            url = arguments.get("url")
            URLValidator.validate_url(url)

            fields = arguments.get("fields", [])
            FieldValidator.validate_fields(fields)

            format_type = arguments.get("format", "json")
            FormatValidator.validate_format(format_type)

            api_key = arguments.get("api_key")
            model_name = arguments.get("model_name")

            if api_key or model_name:
                from ...scraper import WebAgent
                scraper = WebAgent(
                    api_key=api_key,
                    model_name=model_name
                )

            if fields:
                scraper.set_fields(fields)

            result = scraper.scrape_url(
                url=url,
                save_to_file=arguments.get("save_to_file", False),
                format=format_type
            )

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except (ValidationError, ToolExecutionError) as e:
            return [types.TextContent(
                type="text",
                text=json.dumps(e.to_dict())
            )]
        except Exception as e:
            logger.exception(f"Error in {self.name} tool")
            error = ToolExecutionError(f"Tool execution failed: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps(error.to_dict())
            )]


class ScrapeMultipleURLsTool(BaseTool):
    """Tool for scraping multiple URLs."""

    @property
    def name(self) -> str:
        return "scrape_multiple_urls"

    @property
    def description(self) -> str:
        return "Scrape multiple URLs and extract structured data"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to scrape"
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of fields to extract from each URL",
                    "default": []
                },
                "api_key": {
                    "type": "string",
                    "description": "AI provider API key (optional if set in environment)",
                    "default": None
                },
                "model_name": {
                    "type": "string",
                    "description": "AI model to use",
                    "default": None
                },
                "format": {
                    "type": "string",
                    "enum": ["json", "csv"],
                    "description": "Output format",
                    "default": "json"
                },
                "save_to_files": {
                    "type": "boolean",
                    "description": "Whether to save outputs to files",
                    "default": False
                }
            },
            "required": ["urls"]
        }

    async def execute(self, arguments: Dict[str, Any], scraper) -> List[types.TextContent]:
        """Execute the scrape_multiple_urls tool."""
        try:
            urls = arguments.get("urls", [])
            URLValidator.validate_urls(urls)

            fields = arguments.get("fields", [])
            FieldValidator.validate_fields(fields)

            format_type = arguments.get("format", "json")
            FormatValidator.validate_format(format_type)

            api_key = arguments.get("api_key")
            model_name = arguments.get("model_name")

            if api_key or model_name:
                from ...scraper import WebAgent
                scraper = WebAgent(
                    api_key=api_key,
                    model_name=model_name
                )

            if fields:
                scraper.set_fields(fields)

            results = scraper.scrape_multiple_urls(
                urls=urls,
                save_to_files=arguments.get("save_to_files", False),
                format=format_type
            )

            return [types.TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )]

        except (ValidationError, ToolExecutionError) as e:
            return [types.TextContent(
                type="text",
                text=json.dumps(e.to_dict())
            )]
        except Exception as e:
            logger.exception(f"Error in {self.name} tool")
            error = ToolExecutionError(f"Tool execution failed: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps(error.to_dict())
            )]


class ConfigureScraperTool(BaseTool):
    """Tool for configuring scraper settings."""

    @property
    def name(self) -> str:
        return "configure_scraper"

    @property
    def description(self) -> str:
        return "Configure scraper settings like API key, model, and default fields"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "AI provider API key",
                    "default": None
                },
                "model_name": {
                    "type": "string",
                    "description": "AI model to use",
                    "default": None
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Default fields to extract",
                    "default": []
                },
                "temp_dir": {
                    "type": "string",
                    "description": "Temporary directory for processing",
                    "default": "temp"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Output directory for saved files",
                    "default": "output"
                }
            },
            "required": []
        }

    async def execute(self, arguments: Dict[str, Any], scraper) -> List[types.TextContent]:
        """Execute the configure_scraper tool."""
        try:
            fields = arguments.get("fields", [])
            FieldValidator.validate_fields(fields)

            api_key = arguments.get("api_key")
            model_name = arguments.get("model_name")
            temp_dir = arguments.get("temp_dir", "temp")
            output_dir = arguments.get("output_dir", "output")

            from ...scraper import WebAgent
            scraper_instance = WebAgent(
                api_key=api_key,
                model_name=model_name,
                temp_dir=temp_dir,
                output_dir=output_dir
            )

            if fields:
                scraper_instance.set_fields(fields)

            config = {
                "status": "configured",
                "model_name": scraper_instance.get_model_name(),
                "fields": scraper_instance.get_fields(),
                "temp_dir": temp_dir,
                "output_dir": output_dir
            }

            return [types.TextContent(
                type="text",
                text=json.dumps(config, indent=2)
            )]

        except (ValidationError, ToolExecutionError) as e:
            return [types.TextContent(
                type="text",
                text=json.dumps(e.to_dict())
            )]
        except Exception as e:
            logger.exception(f"Error in {self.name} tool")
            error = ToolExecutionError(f"Tool execution failed: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps(error.to_dict())
            )]


class GetScraperInfoTool(BaseTool):
    """Tool for getting scraper information."""

    @property
    def name(self) -> str:
        return "get_scraper_info"

    @property
    def description(self) -> str:
        return "Get current scraper configuration and status"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, arguments: Dict[str, Any], scraper) -> List[types.TextContent]:
        """Execute the get_scraper_info tool."""
        try:
            info = {
                "model_name": scraper.get_model_name(),
                "fields": scraper.get_fields(),
                "cache_stats": scraper.get_cache_stats() if hasattr(scraper, 'get_cache_stats') else None
            }

            return [types.TextContent(
                type="text",
                text=json.dumps(info, indent=2)
            )]

        except Exception as e:
            logger.exception(f"Error in {self.name} tool")
            error = ToolExecutionError(f"Tool execution failed: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps(error.to_dict())
            )]


class ClearCacheTool(BaseTool):
    """Tool for clearing scraper cache."""

    @property
    def name(self) -> str:
        return "clear_cache"

    @property
    def description(self) -> str:
        return "Clear the scraper's cache"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days_old": {
                    "type": "integer",
                    "description": "Clear cache entries older than this many days (0 = clear all)",
                    "default": 0
                }
            },
            "required": []
        }

    async def execute(self, arguments: Dict[str, Any], scraper) -> List[types.TextContent]:
        """Execute the clear_cache tool."""
        try:
            days_old = arguments.get("days_old", 0)

            if days_old > 0:
                removed = scraper.cleanup_old_cache(days_old)
                message = f"Removed {removed} cache entries older than {days_old} days"
            else:
                scraper.clear_cache()
                message = "Cleared all cache entries"

            return [types.TextContent(
                type="text",
                text=json.dumps({"status": "success", "message": message})
            )]

        except Exception as e:
            logger.exception(f"Error in {self.name} tool")
            error = ToolExecutionError(f"Tool execution failed: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps(error.to_dict())
            )]


class ToolManager:
    """Manager class for MCP tools."""

    def __init__(self):
        self._tools = {
            "scrape_url": ScrapeURLTool(),
            "scrape_multiple_urls": ScrapeMultipleURLsTool(),
            "configure_scraper": ConfigureScraperTool(),
            "get_scraper_info": GetScraperInfoTool(),
            "clear_cache": ClearCacheTool()
        }

    def get_all_tools(self) -> List[types.Tool]:
        """Get all available tools as MCP Tool objects."""
        return [tool.to_mcp_tool() for tool in self._tools.values()]

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    async def execute_tool(self, name: str, arguments: Dict[str, Any], scraper) -> List[types.TextContent]:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            error = ToolExecutionError(f"Unknown tool: {name}")
            return [types.TextContent(
                type="text",
                text=json.dumps(error.to_dict())
            )]

        return await tool.execute(arguments, scraper)
