"""
Optimize content by collapsing text, removing empty elements, and whitespace
"""
import re
from bs4 import NavigableString
from .base_cleaner import BaseHtmlCleaner


class ContentOptimizer(BaseHtmlCleaner):
    """Handles content optimization and compression"""

    def remove_empty_divs_recursive(self, soup):
        """Recursively remove empty div elements starting from innermost"""

        def has_meaningful_content(element):
            """Check if an element has meaningful text content"""
            if not element:
                return False

            # Get text content and strip whitespace
            text = element.get_text(strip=True)
            if text:
                return True

            # Check for meaningful attributes that indicate the div serves a purpose
            meaningful_tags = [
                "img", "input", "button", "a", "form", "iframe",
                "video", "audio", "canvas", "svg"
            ]
            for tag in meaningful_tags:
                if element.find(tag):
                    return True

            # Check for data attributes or specific classes that might indicate functionality
            if element.get("data-") or element.get("id"):
                # Be more selective - only keep if it seems functional
                attrs = element.attrs
                for attr_name in attrs:
                    if attr_name.startswith("data-") and not attr_name.startswith("data-testid"):
                        return True
                    if attr_name == "id" and not any(
                        x in str(attrs[attr_name]).lower()
                        for x in ["placeholder", "skeleton", "loading"]
                    ):
                        return True

            return False

        def remove_empty_divs_pass(soup):
            """Single pass of empty div removal"""
            removed_count = 0

            # Find all div elements, starting from deepest nesting
            all_divs = soup.find_all("div")

            # Sort by nesting depth (deepest first)
            divs_by_depth = []
            for div in all_divs:
                depth = len(list(div.parents))
                divs_by_depth.append((depth, div))

            # Sort by depth in descending order (deepest first)
            divs_by_depth.sort(key=lambda x: x[0], reverse=True)

            for depth, div in divs_by_depth:
                if div.parent is None:  # Already removed
                    continue

                if not has_meaningful_content(div):
                    # Check if removing this div would break structure
                    parent = div.parent
                    if parent and parent.name in ["html", "head", "body"]:
                        # Don't remove direct children of important structural elements
                        # unless they're completely empty
                        if not div.get_text(strip=True) and not div.find_all():
                            div.decompose()
                            removed_count += 1
                    else:
                        div.decompose()
                        removed_count += 1

            return removed_count

        # Keep removing empty divs until no more can be removed
        total_removed = 0
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            removed_this_pass = remove_empty_divs_pass(soup)
            total_removed += removed_this_pass

            if removed_this_pass == 0:
                break  # No more empty divs to remove

            iteration += 1

        self.logger.info(
            f"Removed {total_removed} empty div elements in {iteration} iterations"
        )
        return soup

    def remove_whitespace_between_tags(self, html_content):
        """
        Remove whitespace and newlines only between consecutive tags
        while preserving text content within tags.
        """
        original_length = len(html_content)

        # Remove whitespace between closing tag and opening tag
        cleaned_html = re.sub(r">\s+<", "><", html_content)

        # Also remove leading/trailing whitespace from lines
        lines = cleaned_html.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped_line = line.strip()
            if stripped_line:  # Only keep non-empty lines
                cleaned_lines.append(stripped_line)

        # Join lines without extra newlines
        final_html = "".join(cleaned_lines)

        final_length = len(final_html)
        reduction_percent = (
            ((original_length - final_length) / original_length * 100)
            if original_length > 0 else 0
        )

        self.logger.info(
            f"Removed whitespace between tags. "
            f"Length: {original_length} → {final_length} "
            f"({reduction_percent:.1f}% reduction)"
        )

        return final_html

    def collapse_text(self, text):
        """
        Collapse long text nodes - Replace lengthy text with short placeholders
        """
        text = text.strip()
        if len(text) <= 30:
            return text  # Keep short text intact
        elif len(text) <= 100:
            return text[:50] + "..."  # Medium text - keep first 50 chars
        else:
            return text[:30] + "..." + text[-20:]  # Long text - keep start + end

    def collapse_long_text_nodes(self, soup):
        """
        Apply text collapsing to all text nodes in the HTML document
        """
        collapsed_count = 0

        # Get all text nodes that are direct content (not attributes)
        text_nodes = soup.find_all(string=True)

        for text_node in text_nodes:
            if isinstance(text_node, NavigableString):
                original_text = str(text_node)
                # Skip if text is too short or mostly whitespace
                if len(original_text.strip()) <= 30:
                    continue

                # Collapse the text
                collapsed_text = self.collapse_text(original_text)

                # Replace if text was actually collapsed
                if collapsed_text != original_text:
                    text_node.replace_with(collapsed_text)
                    collapsed_count += 1

        self.logger.info(f"Collapsed {collapsed_count} long text nodes")
        return soup
