"""
Universal Scraper - AI-powered web scraping with customizable field extraction

This module provides an easy-to-use interface for scraping web content
and extracting structured data using AI.
"""

from .scraper import UniversalScraper, scrape
from .browser import browse

__version__ = "1.9.7"
__author__ = "Witeso"
__email__ = "support@witeso.com"

__all__ = ["UniversalScraper", "scrape", "browse"]
