"""
HTML Cleaning Components

This package provides modular HTML cleaning functionality split into focused components:
- base_cleaner: Base classes and common utilities
- noise_remover: Remove scripts, styles, comments, SVG, iframes
- url_replacer: Replace URLs with placeholders
- structure_cleaner: Remove headers/footers, focus on main content
- content_optimizer: Text collapsing, empty divs, whitespace removal
- duplicate_finder: Find and remove repeating structures
- attribute_cleaner: Remove non-essential attributes
- html_cleaner: Main orchestrator that coordinates all cleaning steps
"""

from .html_cleaner import HtmlCleaner

__all__ = ['HtmlCleaner']
