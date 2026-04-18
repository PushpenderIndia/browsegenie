"""
universal_scraper.core.web_ui
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Local web UI package for Universal Scraper.

Public surface:
  main()        — CLI entry point (universal-scraper-ui command)
  create_app()  — Flask application factory
"""

from .cli import main
from .server import create_app

__all__ = ["main", "create_app"]
