"""
WebAgent Module
A Python module for AI-powered web scraping with customizable field extraction.

Usage:
    from webagent import WebAgent

    scraper = WebAgent(api_key="your_gemini_api_key")
    scraper.set_fields(
        ["company_name", "job_title", "apply_link", "salary_range"]
    )
    data = scraper.scrape_url("https://example.com/jobs")
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

from .core.html_fetcher import HtmlFetcher
from .core.html_cleaner import HtmlCleaner
from .core.data_extractor import DataExtractor

try:
    from litellm import completion

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    completion = None


class WebAgent:
    """
    A modular web scraping system that fetches HTML, cleans it, and extracts
    structured data using AI with customizable field extraction.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        temp_dir: str = "temp",
        output_dir: str = "output",
        log_level: int = logging.INFO,
        model_name: Optional[str] = None,
    ):
        """
        Initialize the WebAgent.

        Args:
            api_key: AI provider API key. For Gemini, can use
                    GEMINI_API_KEY env var.
                    For other providers, must be provided or set
                    appropriate env vars.
            temp_dir: Directory for temporary files
            output_dir: Directory for output files
            log_level: Logging level
            model_name: Model name. If None, defaults to
                       'gemini-2.5-flash' for Gemini.
                       Examples: 'gemini-2.5-flash', 'gpt-4',
                       'claude-3-sonnet', etc.
        """
        self.setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        self.temp_dir = temp_dir
        self.output_dir = output_dir
        self.api_key = api_key
        # Set default model based on API key detection if not provided
        if model_name is None:
            self.model_name = self._detect_default_model(api_key)
        else:
            self.model_name = model_name
        self.extraction_fields = [
            "company_name",
            "job_title",
            "apply_link",
            "salary_range",
        ]

        # Create directories
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Initialize modules
        self.fetcher = HtmlFetcher(temp_dir=temp_dir)
        self.cleaner = HtmlCleaner(temp_dir=temp_dir)

        # Initialize extractor with custom fields support and caching
        self.extractor = CustomDataExtractor(
            api_key=api_key,
            temp_dir=temp_dir,
            output_dir=output_dir,
            fields=self.extraction_fields,
            model_name=model_name,
            enable_cache=True,
        )

    def setup_logging(self, level: int):
        """Setup logging configuration"""
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def set_fields(self, fields: List[str]) -> None:
        """
        Set the fields to extract from web pages.

        Args:
            fields: List of field names to extract
                   (e.g., ["company_name", "job_title"])
        """
        if not fields or not isinstance(fields, list):
            raise ValueError("Fields must be a non-empty list")

        self.extraction_fields = fields
        self.extractor.set_fields(fields)
        self.logger.info(f"Extraction fields updated: {fields}")

    def get_fields(self) -> List[str]:
        """
        Get the currently configured extraction fields.

        Returns:
            List of field names currently configured for extraction
        """
        return self.extraction_fields.copy()

    def get_model_name(self) -> str:
        """
        Get the currently configured Gemini model name.

        Returns:
            Name of the Gemini model being used
        """
        return self.extractor.model_name

    def set_model_name(self, model_name: str) -> None:
        """
        Change the AI model.

        Args:
            model_name: Name of the AI model to use
                       Examples: 'gemini-2.5-flash', 'gpt-4',
                       'claude-3-sonnet', etc.
        """
        self.model_name = model_name
        self.extractor.model_name = model_name
        # Re-initialize the AI provider with new model
        self.extractor._initialize_ai_provider(self.api_key)
        self.logger.info(f"Model changed to: {model_name}")

    def scrape_url(
        self,
        url: str,
        save_to_file: bool = False,
        output_filename: Optional[str] = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Scrape a single URL and return extracted data.

        Args:
            url: URL to scrape
            save_to_file: Whether to save results to a file
            output_filename: Custom output filename (optional)
            format: Output format - 'json' (default) or 'csv'

        Returns:
            Dictionary containing extracted data and metadata
        """
        self.logger.info(f"Starting scraping for: {url}")

        if not self._validate_url(url):
            raise ValueError(f"Invalid URL format: {url}")

        try:
            # Step 1: Fetch HTML
            raw_html = self.fetcher.fetch_html(url)

            # Step 2: Clean HTML (for AI analysis)
            cleaned_html = self.cleaner.clean_html(raw_html, url=url)

            # Step 3: Extract structured data (use cleaned HTML for code
            # generation, original for execution)
            extracted_data = self.extractor.extract_data_with_separation(
                cleaned_html, raw_html, url
            )

            result = {
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "fields": self.extraction_fields,
                "data": extracted_data,
                "metadata": {
                    "raw_html_length": len(raw_html),
                    "cleaned_html_length": len(cleaned_html),
                    "items_extracted": (
                        len(extracted_data)
                        if isinstance(extracted_data, list)
                        else 1
                    ),
                },
            }

            # Optionally save to file
            if save_to_file:
                filename = output_filename or self._generate_filename(
                    url, format
                )
                filepath = self._save_data(result, filename, format)
                result["saved_to"] = filepath

            self.logger.info(f"Successfully extracted data from {url}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {str(e)}")
            raise

    def scrape_multiple_urls(
        self, urls: List[str], save_to_files: bool = True, format: str = "json"
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs.

        Args:
            urls: List of URLs to scrape
            save_to_files: Whether to save results to individual files
            format: Output format - 'json' (default) or 'csv'

        Returns:
            List of results for each URL
        """
        results = []

        for i, url in enumerate(urls, 1):
            self.logger.info(f"Processing URL {i}/{len(urls)}: {url}")

            try:
                result = self.scrape_url(
                    url, save_to_file=save_to_files, format=format
                )
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to scrape {url}: {str(e)}")
                results.append(
                    {
                        "url": url,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return self.extractor.get_cache_stats()

    def clear_cache(self) -> bool:
        """
        Clear the extraction code cache.

        Returns:
            True if cleared successfully, False otherwise
        """
        return self.extractor.clear_cache()

    def cleanup_old_cache(self, days_old: int = 30) -> int:
        """
        Clean up cache entries older than specified days.

        Args:
            days_old: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        return self.extractor.cleanup_old_cache(days_old)

    def _detect_default_model(self, api_key: Optional[str]) -> str:
        """
        Detect default model based on API key pattern or environment variables.

        Args:
            api_key: API key provided by user

        Returns:
            Default model name
        """
        # Check for specific environment variables to detect provider
        if os.getenv("OPENAI_API_KEY") and not api_key:
            return "gpt-4o-mini"
        elif os.getenv("ANTHROPIC_API_KEY") and not api_key:
            return "claude-3-haiku-20240307"
        elif os.getenv("GEMINI_API_KEY") or not api_key:
            return "gemini-2.5-flash"

        # If API key is provided, try to detect from key pattern
        if api_key:
            if api_key.startswith("sk-"):
                return "gpt-4o-mini"  # OpenAI pattern
            elif api_key.startswith("sk-ant-"):
                return "claude-3-haiku-20240307"  # Anthropic pattern
            elif "AIza" in api_key:
                return "gemini-2.5-flash"  # Google AI Studio pattern

        # Default to Gemini if nothing else detected
        return "gemini-2.5-flash"

    def disable_cache(self) -> None:
        """Disable caching for this scraper instance"""
        self.extractor.enable_cache = False
        self.logger.info("Caching disabled")

    def enable_cache(self) -> None:
        """Enable caching for this scraper instance"""
        self.extractor.enable_cache = True
        self.logger.info("Caching enabled")

    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc]) and parsed.scheme in [
                "http",
                "https",
            ]
        except Exception:
            return False

    def _generate_filename(self, url: str, format: str = "json") -> str:
        """Generate filename based on URL and format"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "").replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = "json" if format.lower() == "json" else "csv"
        return f"{domain}_{timestamp}.{extension}"

    def _save_data(
        self, data: Dict[str, Any], filename: str, format: str = "json"
    ) -> str:
        """Save data to JSON or CSV file"""
        if not os.path.dirname(filename):
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = filename

        if format.lower() == "csv":
            self._save_as_csv(data, filepath)
        else:
            self._save_as_json(data, filepath)

        return filepath

    def _save_as_json(self, data: Dict[str, Any], filepath: str) -> None:
        """Save data as JSON file"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_as_csv(self, data: Dict[str, Any], filepath: str) -> None:
        """Save data as CSV file"""
        import csv

        # Extract the actual data from the result structure
        extracted_data = data.get("data", [])

        if not extracted_data:
            raise ValueError("No data to save to CSV")

        # Convert single item to list for consistent processing
        if isinstance(extracted_data, dict):
            data_list = [extracted_data]
        else:
            data_list = extracted_data

        # Get all unique field names from all items
        fieldnames = set()
        for item in data_list:
            if isinstance(item, dict):
                fieldnames.update(item.keys())

        fieldnames = sorted(list(fieldnames))

        with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header
            writer.writeheader()

            # Write data rows
            for item in data_list:
                if isinstance(item, dict):
                    # Ensure all fields are present, fill missing with
                    # empty string
                    row = {field: item.get(field, "") for field in fieldnames}
                    writer.writerow(row)


class CustomDataExtractor(DataExtractor):
    """
    Extended DataExtractor that supports custom field configuration
    with caching
    """

    def __init__(
        self,
        api_key=None,
        temp_dir="temp",
        output_dir="output",
        fields=None,
        model_name=None,
        enable_cache=True,
    ):
        super().__init__(
            api_key, temp_dir, output_dir, model_name, enable_cache
        )
        self.fields = fields or [
            "company_name",
            "job_title",
            "apply_link",
            "salary_range",
        ]

    def set_fields(self, fields: List[str]) -> None:
        """Set the fields to extract"""
        self.fields = fields

    def get_extraction_fields(self):
        """Override to return current custom fields"""
        return self.fields

    def extract_data(self, html_content, url=None):
        """Extract data using the current field configuration with caching"""
        try:
            # Use parent class method which now handles caching
            return super().extract_data(html_content, url, self.fields)

        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            raise

    def extract_data_with_separation(
        self, cleaned_html, original_html, url=None
    ):
        """Extract data using cleaned HTML for code generation and
        original HTML for execution"""
        try:
            return super().extract_data_with_separation(
                cleaned_html, original_html, url, self.fields
            )
        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            raise


# Convenience function for quick usage
def scrape(
    url: str,
    api_key: str,
    fields: List[str],
    model_name: Optional[str] = None,
    format: str = "json",
) -> Dict[str, Any]:
    """
    Quick scraping function for simple use cases.

    Args:
        url: URL to scrape
        api_key: AI provider API key
        fields: List of fields to extract
        model_name: AI model name (optional, auto-detects based on
                   api_key pattern)
        format: Output format - 'json' (default) or 'csv'

    Returns:
        Extracted data dictionary
    """
    scraper = WebAgent(api_key=api_key, model_name=model_name)
    scraper.set_fields(fields)
    return scraper.scrape_url(url, format=format)


# Example usage
if __name__ == "__main__":
    # Example of how to use the module

    # Initialize scraper - will auto-detect model based on available API keys
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )
    if not api_key:
        print(
            "Please set one of: GEMINI_API_KEY, OPENAI_API_KEY, "
            "or ANTHROPIC_API_KEY environment variable"
        )
        exit(1)

    # Initialize scraper with custom model (optional)
    scraper = WebAgent(api_key=api_key, model_name="gemini-2.5-flash")

    # Set custom fields
    scraper.set_fields(
        ["company_name", "job_title", "apply_link", "salary_range"]
    )

    # Check current model
    print(f"Using model: {scraper.get_model_name()}")

    # Scrape a URL
    try:
        result = scraper.scrape_url(
            "https://example.com/jobs", save_to_file=True
        )
        print(
            "Successfully scraped data: "
            f"{result['metadata']['items_extracted']} items"
        )
        print(f"Fields extracted: {result['fields']}")
        if result.get("saved_to"):
            print(f"Data saved to: {result['saved_to']}")
    except Exception as e:
        print(f"Scraping failed: {e}")
