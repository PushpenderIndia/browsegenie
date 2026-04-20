"""
Remove non-essential HTML attributes
"""
from .base_cleaner import BaseHtmlCleaner


class AttributeCleaner(BaseHtmlCleaner):
    """Handles removal of non-essential HTML attributes"""

    def remove_non_essential_attributes(self, soup):
        """
        Remove non-essential HTML attributes that don't affect data extraction.
        """
        removed_count = 0
        total_attributes_before = 0

        # Get all elements with attributes
        all_elements = soup.find_all(lambda tag: tag.attrs)

        for element in all_elements:
            if not element.attrs:
                continue

            original_attrs = dict(element.attrs)
            total_attributes_before += len(original_attrs)
            attributes_to_remove = []

            for attr_name in original_attrs:
                # Skip if it's an essential attribute
                if attr_name in self.essential_attributes:
                    continue

                # Check for exact matches
                if attr_name in self.remove_attributes:
                    attributes_to_remove.append(attr_name)
                    continue

                # Check for pattern matches (like data-* attributes)
                should_remove = False
                for remove_pattern in self.remove_attributes:
                    if remove_pattern.endswith("-") and attr_name.startswith(remove_pattern):
                        # Handle patterns like 'data-og-', 'ng-', etc.
                        should_remove = True
                        break

                if should_remove:
                    attributes_to_remove.append(attr_name)
                    continue

                # Special handling for data attributes - be more selective
                if attr_name.startswith("data-"):
                    # Check if it's a data attribute that might contain useful content
                    data_key = attr_name[5:]  # Remove 'data-' prefix

                    # Keep data attributes that are likely to contain extractable content
                    useful_data_patterns = [
                        "price", "value", "id", "name", "title", "url", "link", "href",
                        "date", "time", "location", "address", "phone", "email", "contact",
                        "rating", "review", "score", "count", "quantity", "amount", "number",
                        "currency", "cost", "fee", "discount", "sale", "offer", "status",
                        "state", "condition", "availability", "stock", "category", "type",
                        "tag", "genre", "classification", "brand", "model", "sku", "product",
                        "item", "article", "description", "summary", "content", "text", "body",
                        "author", "creator", "publisher", "source", "size", "dimension",
                        "weight", "length", "width", "height", "color", "material",
                        "specification", "feature"
                    ]

                    # Keep the data attribute if it matches useful patterns
                    if any(pattern in data_key.lower() for pattern in useful_data_patterns):
                        continue

                # If we get here, check if it's in our removal list
                if attr_name in self.remove_attributes:
                    attributes_to_remove.append(attr_name)

            # Remove the identified attributes
            for attr_name in attributes_to_remove:
                if attr_name in element.attrs:
                    del element.attrs[attr_name]
                    removed_count += 1

        total_attributes_after = sum(
            len(el.attrs) for el in soup.find_all(lambda tag: tag.attrs)
        )

        self.logger.info(
            f"Removed {removed_count} non-essential attributes "
            f"({total_attributes_before} → {total_attributes_after})"
        )

        return soup
