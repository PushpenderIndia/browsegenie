"""
universal_scraper.web_ui
~~~~~~~~~~~~~~~~~~~~~~~~
Thin shim that preserves the `universal-scraper-ui` console-script entry point.

All implementation lives in universal_scraper/core/web_ui/.
"""

from .core.web_ui import create_app, main  # noqa: F401

__all__ = ["main", "create_app"]
