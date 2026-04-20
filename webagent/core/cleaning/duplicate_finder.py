"""
Find and remove duplicate/repeating HTML structures
"""
import hashlib
from difflib import SequenceMatcher
from .base_cleaner import BaseHtmlCleaner


class DuplicateFinder(BaseHtmlCleaner):
    """Handles detection and removal of duplicate/repeating structures"""

    def get_element_signature(self, element):
        """Generate a signature for an element based on its structure"""
        if not element.name:
            return None

        # Create signature from tag structure, classes, and attribute patterns
        signature_parts = []

        # Tag name
        signature_parts.append(element.name)

        # Classes (sorted for consistency)
        if element.get("class"):
            classes = sorted(element.get("class"))
            signature_parts.append("classes:" + ",".join(classes))

        # Important attributes (excluding unique identifiers)
        important_attrs = ["role", "type", "data-*"]
        for attr in element.attrs:
            if attr in important_attrs or attr.startswith("data-"):
                signature_parts.append(f"{attr}:{element.attrs[attr]}")

        # Child element structure (first level only)
        child_tags = []
        for child in element.children:
            if hasattr(child, "name") and child.name:
                child_tags.append(child.name)
        if child_tags:
            signature_parts.append("children:" + ",".join(sorted(set(child_tags))))

        return "|".join(signature_parts)

    def get_structural_hash(self, element):
        """Generate a structural hash for an element based on its DOM structure"""

        def get_element_tree_structure(elem, max_depth=3, current_depth=0):
            """Recursively build a structure representation"""
            if (
                current_depth >= max_depth
                or not hasattr(elem, "name")
                or not elem.name
            ):
                return ""

            structure_parts = [elem.name]

            # Add important attributes (sorted for consistency)
            if elem.get("class"):
                structure_parts.append(f"class:{','.join(sorted(elem.get('class')))}")

            # Add child structure
            child_structures = []
            for child in elem.children:
                if hasattr(child, "name") and child.name:
                    child_structure = get_element_tree_structure(
                        child, max_depth, current_depth + 1
                    )
                    if child_structure:
                        child_structures.append(child_structure)

            if child_structures:
                structure_parts.append(f"children:[{','.join(child_structures)}]")

            return "|".join(structure_parts)

        structure_str = get_element_tree_structure(element)
        return hashlib.sha256(structure_str.encode()).hexdigest()[:16]

    def find_repeating_structures(
        self, soup, min_keep=2, min_total=3, similarity_threshold=0.85
    ):
        """
        Find repeating HTML structures and return elements to remove.
        """
        body = soup.find("body")
        if not body:
            return []

        # Get potential repeating containers
        candidates = body.find_all(
            ["div", "article", "section", "li", "tr"], recursive=True
        )

        # Filter candidates - focus on meaningful containers
        meaningful_candidates = []
        for elem in candidates:
            elem_str = str(elem)
            elem_text = elem.get_text(strip=True)

            # Skip if too small, too large, or mostly empty
            if (
                len(elem_str) < 200 or len(elem_str) > 10000
                or len(elem_text) < 10 or len(elem_text) > 2000
            ):
                continue

            # Skip if it's mostly nested (likely a wrapper)
            direct_text = elem.get_text(strip=True)
            child_text = ""
            for child in elem.children:
                if hasattr(child, "get_text"):
                    child_text += child.get_text(strip=True)

            if len(direct_text) < len(child_text) * 0.1:  # Less than 10% direct content
                continue

            meaningful_candidates.append(elem)

        # Group by structural hash
        structure_groups = {}
        for elem in meaningful_candidates:
            struct_hash = self.get_structural_hash(elem)
            if struct_hash not in structure_groups:
                structure_groups[struct_hash] = []
            structure_groups[struct_hash].append(elem)

        # Find similar structures using SequenceMatcher
        similar_groups = {}
        processed_hashes = set()

        for hash1, group1 in structure_groups.items():
            if hash1 in processed_hashes or len(group1) < min_total:
                continue

            # Start a new similarity group
            similar_group = list(group1)
            group_key = hash1
            processed_hashes.add(hash1)

            # Compare with other groups
            for hash2, group2 in structure_groups.items():
                if hash2 in processed_hashes or len(group2) < min_total:
                    continue

                # Use SequenceMatcher to compare structure strings
                elem1_str = self.get_element_signature(group1[0]) or ""
                elem2_str = self.get_element_signature(group2[0]) or ""

                similarity = SequenceMatcher(None, elem1_str, elem2_str).ratio()

                if similarity >= similarity_threshold:
                    similar_group.extend(group2)
                    processed_hashes.add(hash2)

            if len(similar_group) >= min_total:
                similar_groups[group_key] = similar_group

        # Determine which elements to remove
        elements_to_remove = []

        for group_key, elements in similar_groups.items():
            if len(elements) >= min_total:
                # Sort by position in document to keep the first ones
                elements_with_pos = []
                for elem in elements:
                    pos = 0
                    current = elem
                    while current.previous_sibling:
                        pos += 1
                        current = current.previous_sibling
                    elements_with_pos.append((pos, elem))

                # Sort by position and keep only the first min_keep elements
                elements_with_pos.sort(key=lambda x: x[0])
                elements_to_keep = [elem for _, elem in elements_with_pos[:min_keep]]
                elements_to_remove_from_group = [
                    elem for _, elem in elements_with_pos[min_keep:]
                ]

                elements_to_remove.extend(elements_to_remove_from_group)

                self.logger.info(
                    f"Found {len(elements)} similar structures, "
                    f"keeping {len(elements_to_keep)}, "
                    f"removing {len(elements_to_remove_from_group)}"
                )

        return elements_to_remove

    def remove_repeating_structures(
        self, soup, min_keep=2, min_total=3, similarity_threshold=0.85
    ):
        """Remove repeating structures while keeping a sample of each type"""
        elements_to_remove = self.find_repeating_structures(
            soup, min_keep, min_total, similarity_threshold
        )

        removed_count = 0
        for element in elements_to_remove:
            if element.parent:  # Check if still in tree
                element.decompose()
                removed_count += 1

        self.logger.info(f"Removed {removed_count} repeating structure elements")
        return soup
