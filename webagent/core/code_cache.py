import os
import json
import hashlib
import sqlite3
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup


class CodeCache:
    """
    A caching system for BeautifulSoup extraction codes.
    Stores generated codes based on URL (without query params) and
    structural hash.
    """

    def __init__(
        self, db_path: str = "extraction_cache.db", cache_dir: str = "cache"
    ):
        """
        Initialize the code cache.

        Args:
            db_path: Path to SQLite database file
            cache_dir: Directory to store cached extraction codes
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.cache_dir = cache_dir

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

        # Initialize database
        self._init_database()

        self.logger.info(f"CodeCache initialized with database: {db_path}")

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create cache table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS extraction_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_clean TEXT NOT NULL,
                    structural_hash TEXT NOT NULL,
                    fields_hash TEXT NOT NULL,
                    extraction_code TEXT NOT NULL,
                    code_file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    use_count INTEGER DEFAULT 1,
                    UNIQUE(url_clean, structural_hash, fields_hash)
                )
            """
            )

            # Create index for faster lookups
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_url_hash
                ON extraction_cache(url_clean, structural_hash, fields_hash)
            """
            )

            conn.commit()
            self.logger.debug("Database initialized successfully")

    def _clean_url(self, url: str) -> str:
        """
        Clean URL by removing query parameters and fragments.

        Args:
            url: Original URL

        Returns:
            Cleaned URL without query parameters
        """
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        # Remove trailing slash for consistency
        if clean_url.endswith("/") and len(clean_url) > 1:
            clean_url = clean_url[:-1]
        return clean_url

    def _compute_structural_hash(self, html_content: str) -> str:
        """
        Compute structural hash by replacing all text content with
        placeholders.
        This creates a hash based on HTML structure rather than content.

        Args:
            html_content: Raw HTML content

        Returns:
            SHA256 hash of structural HTML
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements completely
            for element in soup(
                ["script", "style", "meta", "link", "noscript"]
            ):
                element.decompose()

            # Replace all text content with a placeholder
            def replace_text_content(element):
                if element.string:
                    # Replace text with placeholder based on length
                    text_length = len(element.string.strip())
                    if text_length > 0:
                        element.string.replace_with("TEXT_PLACEHOLDER")

                # Handle attributes that might contain dynamic content
                if hasattr(element, "attrs"):
                    attrs_to_clean = [
                        "href",
                        "src",
                        "action",
                        "data-",
                        "id",
                        "title",
                        "alt",
                    ]
                    for attr in list(element.attrs.keys()):
                        # Clean dynamic attributes but preserve structural
                        # ones like class
                        if any(
                            attr.startswith(pattern)
                            for pattern in attrs_to_clean
                        ):
                            if attr in ["href", "src", "action"]:
                                element.attrs[attr] = "URL_PLACEHOLDER"
                            elif attr.startswith("data-"):
                                element.attrs[attr] = "DATA_PLACEHOLDER"
                            elif attr in ["id", "title", "alt"]:
                                element.attrs[attr] = "TEXT_PLACEHOLDER"

            # Recursively process all elements
            for element in soup.find_all(text=True):
                if element.parent:
                    text_content = element.strip()
                    if text_content and element.parent.name not in [
                        "script",
                        "style",
                    ]:
                        element.replace_with("TEXT_PLACEHOLDER")

            # Also clean attributes in all elements
            for element in soup.find_all():
                replace_text_content(element)

            # Get the structural HTML as string
            structural_html = str(soup)

            # Remove extra whitespace and normalize
            structural_html = re.sub(r"\s+", " ", structural_html)
            structural_html = structural_html.strip()

            # Compute SHA256 hash
            hash_object = hashlib.sha256(structural_html.encode("utf-8"))
            structural_hash = hash_object.hexdigest()

            self.logger.debug(f"Computed structural hash: {structural_hash}")
            return structural_hash

        except Exception as e:
            self.logger.error(f"Error computing structural hash: {str(e)}")
            # Fallback to content-based hash
            return hashlib.sha256(html_content.encode("utf-8")).hexdigest()

    def _compute_fields_hash(self, fields: list) -> str:
        """
        Compute hash for the fields configuration.

        Args:
            fields: List of field names

        Returns:
            SHA256 hash of fields configuration
        """
        fields_str = json.dumps(sorted(fields), ensure_ascii=False)
        return hashlib.sha256(fields_str.encode("utf-8")).hexdigest()

    def _save_code_to_file(
        self, code: str, url_clean: str, structural_hash: str
    ) -> str:
        """
        Save extraction code to a file in the cache directory.

        Args:
            code: Extraction code
            url_clean: Clean URL
            structural_hash: Structural hash

        Returns:
            Path to the saved file
        """
        try:
            # Create filename based on URL and hash
            parsed = urlparse(url_clean)
            domain = parsed.netloc.replace("www.", "").replace(".", "_")
            filename = f"{domain}_{structural_hash[:16]}.py"
            filepath = os.path.join(self.cache_dir, filename)

            # Add metadata header to the code
            header = f"""# Cached extraction code
# URL: {url_clean}
# Structural Hash: {structural_hash}
# Generated at: {datetime.now().isoformat()}

"""

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header + code)

            self.logger.debug(f"Code saved to cache file: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Error saving code to file: {str(e)}")
            return None

    def get_cached_code(
        self, url: str, html_content: str, fields: list
    ) -> Optional[str]:
        """
        Retrieve cached extraction code if available.

        Args:
            url: Original URL
            html_content: HTML content for structural hash computation
            fields: List of field names

        Returns:
            Cached extraction code or None if not found
        """
        try:
            url_clean = self._clean_url(url)
            structural_hash = self._compute_structural_hash(html_content)
            fields_hash = self._compute_fields_hash(fields)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Look for cached code
                cursor.execute(
                    """
                    SELECT extraction_code, code_file_path,
                           use_count
                    FROM extraction_cache
                    WHERE url_clean = ? AND structural_hash = ?
                          AND fields_hash = ?
                """,
                    (url_clean, structural_hash, fields_hash),
                )

                result = cursor.fetchone()

                if result:
                    extraction_code, code_file_path, use_count = result

                    # Update usage statistics
                    cursor.execute(
                        """
                        UPDATE extraction_cache
                        SET last_used_at = CURRENT_TIMESTAMP,
                            use_count = use_count + 1
                        WHERE url_clean = ? AND structural_hash = ?
                              AND fields_hash = ?
                    """,
                        (url_clean, structural_hash, fields_hash),
                    )

                    conn.commit()

                    self.logger.info(
                        f"Cache HIT for {url_clean} "
                        f"(used {use_count + 1} times)"
                    )
                    return extraction_code
                else:
                    self.logger.info(f"Cache MISS for {url_clean}")
                    return None

        except Exception as e:
            self.logger.error(f"Error retrieving cached code: {str(e)}")
            return None

    def store_code(
        self, url: str, html_content: str, fields: list, extraction_code: str
    ) -> bool:
        """
        Store extraction code in cache.

        Args:
            url: Original URL
            html_content: HTML content for structural hash computation
            fields: List of field names
            extraction_code: Generated extraction code

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            url_clean = self._clean_url(url)
            structural_hash = self._compute_structural_hash(html_content)
            fields_hash = self._compute_fields_hash(fields)

            # Save code to file
            code_file_path = self._save_code_to_file(
                extraction_code, url_clean, structural_hash
            )

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert or replace the cached code
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO extraction_cache
                    (url_clean, structural_hash, fields_hash,
                     extraction_code, code_file_path)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        url_clean,
                        structural_hash,
                        fields_hash,
                        extraction_code,
                        code_file_path,
                    ),
                )

                conn.commit()

                self.logger.info(
                    f"Code cached for {url_clean} "
                    f"(hash: {structural_hash[:16]}...)"
                )
                return True

        except Exception as e:
            self.logger.error(f"Error storing code in cache: {str(e)}")
            return False

    def clear_cache(self) -> bool:
        """
        Clear all cached codes.

        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM extraction_cache")
                conn.commit()

            # Remove cache files
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith(".py"):
                        os.remove(os.path.join(self.cache_dir, filename))

            self.logger.info("Cache cleared successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get basic stats
                cursor.execute("SELECT COUNT(*) FROM extraction_cache")
                total_entries = cursor.fetchone()[0]

                cursor.execute("SELECT SUM(use_count) FROM extraction_cache")
                total_uses = cursor.fetchone()[0] or 0

                cursor.execute(
                    """
                    SELECT AVG(use_count), MAX(use_count), MIN(use_count)
                    FROM extraction_cache
                """
                )
                avg_uses, max_uses, min_uses = cursor.fetchone()

                # Get top URLs by usage
                cursor.execute(
                    """
                    SELECT url_clean, use_count, last_used_at
                    FROM extraction_cache
                    ORDER BY use_count DESC
                    LIMIT 5
                """
                )
                top_urls = cursor.fetchall()

                return {
                    "total_entries": total_entries,
                    "total_uses": total_uses,
                    "average_uses": round(avg_uses, 2) if avg_uses else 0,
                    "max_uses": max_uses or 0,
                    "min_uses": min_uses or 0,
                    "top_urls": [
                        {"url": url, "uses": uses, "last_used": last_used}
                        for url, uses, last_used in top_urls
                    ],
                }

        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {}

    def cleanup_old_entries(self, days_old: int = 30) -> int:
        """
        Clean up cache entries older than specified days.

        Args:
            days_old: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Delete old entries
                cursor.execute(
                    """
                    DELETE FROM extraction_cache
                    WHERE created_at < datetime('now', '-' || ? || ' days')
                """,
                    (days_old,),
                )

                removed_count = cursor.rowcount
                conn.commit()

                if removed_count > 0:
                    self.logger.info(
                        f"Removed {removed_count} old cache entries"
                    )

                return removed_count

        except Exception as e:
            self.logger.error(f"Error cleaning up old entries: {str(e)}")
            return 0
