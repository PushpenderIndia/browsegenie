"""
Remove noise elements like scripts, styles, comments, SVG, and iframes
"""
from bs4 import Comment
from .base_cleaner import BaseHtmlCleaner


class NoiseRemover(BaseHtmlCleaner):
    """Handles removal of noise elements that don't contribute to content extraction"""

    def remove_noise(self, soup):
        """Remove script tags, styles, comments and other noise"""
        # Remove script and style elements
        for tag_name in self.noise_tags:
            for element in soup.find_all(tag_name):
                element.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        return soup

    def remove_inline_svg_images(self, soup):
        """
        Remove inline SVG images to reduce HTML size and noise.
        SVG elements often contain complex graphics that don't contribute to
        text-based data extraction.
        """
        svg_count = 0
        for svg_element in soup.find_all("svg"):
            svg_element.decompose()
            svg_count += 1

        if svg_count > 0:
            self.logger.info(f"Removed {svg_count} Inline SVG image elements.")

        return soup

    def remove_iframes(self, soup):
        """
        Remove iframe elements to reduce HTML size and eliminate embedded content.
        Iframes often contain ads, tracking pixels, or external content that doesn't
        contribute to data extraction.
        """
        iframe_count = 0
        for iframe_element in soup.find_all("iframe"):
            iframe_element.decompose()
            iframe_count += 1

        if iframe_count > 0:
            self.logger.info(f"Removed {iframe_count} iframe elements.")

        return soup
