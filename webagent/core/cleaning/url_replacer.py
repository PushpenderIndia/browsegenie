"""
Replace URL sources with text placeholders
"""
from .base_cleaner import BaseHtmlCleaner


class UrlReplacer(BaseHtmlCleaner):
    """Handles replacement of URL sources with placeholders"""

    def replace_url_sources_with_placeholders(self, soup):
        """
        Replace URL sources (src, href, action attributes) with text placeholders
        to reduce HTML size while maintaining structure for data extraction.
        """
        url_count = 0

        # Define attributes that typically contain URLs
        url_attributes = ['src', 'href', 'action', 'data-src', 'data-href']

        # Find all elements with URL attributes
        for attr in url_attributes:
            elements = soup.find_all(attrs={attr: True})
            for element in elements:
                original_url = element.get(attr)
                if original_url and original_url.strip():
                    # Skip if it's already a placeholder or very short
                    if len(original_url.strip()) <= 20 or original_url.strip().startswith('[URL'):
                        continue

                    # Create a placeholder based on the URL type
                    if attr in ['src', 'data-src']:
                        if element.name == 'img':
                            placeholder = '[IMG_URL]'
                        elif element.name == 'iframe':
                            placeholder = '[IFRAME_URL]'
                        elif element.name in ['script', 'link']:
                            placeholder = '[RESOURCE_URL]'
                        else:
                            placeholder = '[SRC_URL]'
                    elif attr in ['href', 'data-href']:
                        if element.name == 'a':
                            placeholder = '[LINK_URL]'
                        elif element.name == 'link':
                            placeholder = '[RESOURCE_URL]'
                        else:
                            placeholder = '[HREF_URL]'
                    elif attr == 'action':
                        placeholder = '[FORM_URL]'
                    else:
                        placeholder = '[URL]'

                    # Replace the URL with placeholder
                    element[attr] = placeholder
                    url_count += 1

        if url_count > 0:
            self.logger.info(f"Replaced {url_count} URL sources with placeholders.")

        return soup
