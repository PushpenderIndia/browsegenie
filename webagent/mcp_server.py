#!/usr/bin/env python3
"""
MCP Server for WebAgent

This module implements a Model Context Protocol (MCP) server that exposes
the WebAgent functionality as tools that can be used by AI models.
"""

import asyncio
import logging
from .core.mcp.server import create_and_run_server

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webagent-mcp")


async def main():
    """Main entry point for the MCP server."""
    await create_and_run_server()


def main_sync():
    """Synchronous entry point for console scripts."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
