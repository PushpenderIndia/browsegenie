"""
Clean HTML structure by removing headers/footers and focusing on main content
"""
import re
from bs4 import BeautifulSoup
from .base_cleaner import BaseHtmlCleaner


class StructureCleaner(BaseHtmlCleaner):
    """Handles structural cleaning of HTML documents"""

    def remove_header_footer(self, soup):
        """Remove header and footer elements"""
        # Remove by semantic tags
        for tag_name in self.header_tags + self.footer_tags:
            for element in soup.find_all(tag_name):
                element.decompose()

        # Remove by common class/id patterns
        header_patterns = [
            "header", "nav", "navigation", "menu", "top-bar", "masthead"
        ]
        footer_patterns = ["footer", "bottom", "copyright", "legal"]

        for pattern in header_patterns + footer_patterns:
            # Remove by class
            for element in soup.find_all(class_=re.compile(pattern, re.I)):
                element.decompose()
            # Remove by id
            for element in soup.find_all(id=re.compile(pattern, re.I)):
                element.decompose()

        return soup

    def focus_on_main_content(self, soup):
        """Try to identify and focus on the main content area"""
        main_content_selectors = [
            "main", '[role="main"]', "#main", ".main", "#content", ".content",
            "#main-content", ".main-content", "article", ".article", "#article",
            ".container .content", ".page-content"
        ]

        for selector in main_content_selectors:
            try:
                main_element = soup.select_one(selector)
                if main_element and len(main_element.get_text(strip=True)) > 500:
                    self.logger.info(f"Found main content using selector: {selector}")
                    # Create new soup with just the main content
                    new_soup = BeautifulSoup(str(main_element), "html.parser")
                    return new_soup
            except Exception:
                continue

        # If no main content found, return body content
        body = soup.find("body")
        if body:
            return BeautifulSoup(str(body), "html.parser")

        return soup

    def limit_select_options(self, soup, max_options=2):
        """Limit select tags to keep only a maximum number of option tags"""
        select_tags = soup.find_all("select")
        modified_count = 0

        for select_tag in select_tags:
            option_tags = select_tag.find_all("option")

            if len(option_tags) > max_options:
                # Keep only the first max_options option tags
                options_to_remove = option_tags[max_options:]

                # Remove excess option tags
                for option in options_to_remove:
                    option.decompose()

                modified_count += 1
                self.logger.debug(
                    f"Limited select tag to {max_options} options "
                    f"(removed {len(options_to_remove)} options)"
                )

        if modified_count > 0:
            self.logger.info(
                f"Limited {modified_count} select tags to {max_options} option tags each"
            )

        return soup
