"""
Backward compatibility module for HtmlCleaner.
The actual implementation has been refactored into the cleaning package.
"""

# Import the new modular implementation
from .cleaning.html_cleaner import HtmlCleaner

# Re-export for backward compatibility
__all__ = ['HtmlCleaner']
