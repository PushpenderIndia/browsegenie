"""
Main HTML cleaner orchestrator that coordinates all cleaning components
"""
from bs4 import BeautifulSoup
from .base_cleaner import BaseHtmlCleaner
from .noise_remover import NoiseRemover
from .url_replacer import UrlReplacer
from .structure_cleaner import StructureCleaner
from .content_optimizer import ContentOptimizer
from .duplicate_finder import DuplicateFinder
from .attribute_cleaner import AttributeCleaner


class HtmlCleaner(BaseHtmlCleaner):
    """
    Main HTML cleaner that orchestrates all cleaning operations.

    This class coordinates the cleaning pipeline using specialized components:
    1. Remove noise (scripts, styles, comments, SVG, iframes)
    2. Replace URL sources with placeholders
    3. Remove headers/footers and focus on main content
    4. Optimize content (collapse text, remove empty divs, whitespace)
    5. Remove duplicate structures
    6. Remove non-essential attributes
    """

    def __init__(self, temp_dir="temp"):
        super().__init__(temp_dir)

        # Initialize cleaning components
        self.noise_remover = NoiseRemover(temp_dir)
        self.url_replacer = UrlReplacer(temp_dir)
        self.structure_cleaner = StructureCleaner(temp_dir)
        self.content_optimizer = ContentOptimizer(temp_dir)
        self.duplicate_finder = DuplicateFinder(temp_dir)
        self.attribute_cleaner = AttributeCleaner(temp_dir)

    def clean_html(self, html_content, url=None, save_temp=True):
        """
        Main method to clean HTML content using the complete pipeline.

        Args:
            html_content: Raw HTML content to clean
            url: Optional URL for debugging/temp file naming
            save_temp: Whether to save intermediate files for debugging

        Returns:
            str: Cleaned HTML content
        """
        self.logger.info("Starting HTML cleaning process...")

        soup = BeautifulSoup(html_content, "html.parser")
        original_length = len(str(soup))

        # Step 1: Remove noise
        soup = self.noise_remover.remove_noise(soup)
        step1_html = str(soup)
        self.logger.info(f"Removed noise. Length: {len(step1_html)}")
        if save_temp:
            self.save_temp_html(url, step1_html, "01_removed_noise")

        # Step 2: Remove inline SVG images
        soup = self.noise_remover.remove_inline_svg_images(soup)
        step2_html = str(soup)
        self.logger.info(f"Removed SVG/images. Length: {len(step2_html)}")
        if save_temp:
            self.save_temp_html(url, step2_html, "02_removed_svg_images")

        # Step 2.5: Replace URL sources with placeholders
        soup = self.url_replacer.replace_url_sources_with_placeholders(soup)
        step2_5_html = str(soup)
        self.logger.info(f"Replaced URL sources. Length: {len(step2_5_html)}")
        if save_temp:
            self.save_temp_html(url, step2_5_html, "02_5_replaced_url_sources")

        # Step 3: Remove iframe elements
        soup = self.noise_remover.remove_iframes(soup)
        step3_html = str(soup)
        self.logger.info(f"Removed iframes. Length: {len(step3_html)}")
        if save_temp:
            self.save_temp_html(url, step3_html, "03_removed_iframes")

        # Step 4: Remove headers and footers
        soup = self.structure_cleaner.remove_header_footer(soup)
        step4_html = str(soup)
        self.logger.info(f"Removed headers/footers. Length: {len(step4_html)}")
        if save_temp:
            self.save_temp_html(url, step4_html, "04_removed_header_footer")

        # Step 5: Focus on main content
        soup = self.structure_cleaner.focus_on_main_content(soup)
        step5_html = str(soup)
        self.logger.info(f"Focused on main content. Length: {len(step5_html)}")
        if save_temp:
            self.save_temp_html(url, step5_html, "05_main_content")

        # Step 6: Limit select options to 2
        soup = self.structure_cleaner.limit_select_options(soup, max_options=2)
        step6_html = str(soup)
        self.logger.info(f"Limited select options. Length: {len(step6_html)}")
        if save_temp:
            self.save_temp_html(url, step6_html, "06_limited_select_options")

        # Step 7: Remove empty divs recursively
        soup = self.content_optimizer.remove_empty_divs_recursive(soup)
        step7_html = str(soup)
        self.logger.info(f"Removed empty divs. Length: {len(step7_html)}")
        if save_temp:
            self.save_temp_html(url, step7_html, "07_removed_empty_divs")

        # Step 8: Collapse long text nodes
        soup = self.content_optimizer.collapse_long_text_nodes(soup)
        step8_html = str(soup)
        self.logger.info(f"Collapsed long text nodes. Length: {len(step8_html)}")
        if save_temp:
            self.save_temp_html(url, step8_html, "08_collapsed_text")

        # Step 9: Remove non-essential HTML attributes
        soup = self.attribute_cleaner.remove_non_essential_attributes(soup)
        step9_html = str(soup)
        self.logger.info(f"Removed non-essential attributes. Length: {len(step9_html)}")
        if save_temp:
            self.save_temp_html(url, step9_html, "09_removed_attributes")

        # Step 10: Remove whitespace between consecutive tags
        step10_html = self.content_optimizer.remove_whitespace_between_tags(step9_html)
        if save_temp:
            self.save_temp_html(url, step10_html, "10_removed_whitespace")

        # Step 11: Remove repeating structures (keep samples)
        soup = BeautifulSoup(step10_html, "html.parser")
        soup = self.duplicate_finder.remove_repeating_structures(soup, min_keep=2, min_total=3)
        step11_html = str(soup)
        self.logger.info(f"Removed repeating structures. Length: {len(step11_html)}")
        if save_temp:
            self.save_temp_html(url, step11_html, "11_removed_repeating_structures")

        # Step 12: Remove empty divs again after compression
        soup = self.content_optimizer.remove_empty_divs_recursive(soup)
        step12_html = str(soup)
        self.logger.info(f"Removed empty divs (post-compression). Length: {len(step12_html)}")
        if save_temp:
            self.save_temp_html(url, step12_html, "12_removed_empty_divs_post_compression")

        final_html = step12_html
        final_length = len(final_html)
        if save_temp:
            self.save_temp_html(url, final_html, "13_final_cleaned")

        self.logger.info(f"HTML cleaning completed. Original: {original_length}, Final: {final_length}")
        reduction_percent = (original_length - final_length) / original_length * 100
        self.logger.info(f"Reduction: {reduction_percent:.1f}%")

        return final_html
