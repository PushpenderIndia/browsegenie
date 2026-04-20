import json
import logging
import os
import csv
from datetime import datetime
from urllib.parse import urlparse
from google import genai
from bs4 import BeautifulSoup
from .code_cache import CodeCache
from .token_usage import (
    ApiCallTokens,
    extract_gemini_tokens,
    extract_litellm_tokens,
    summarise,
)

try:
    from litellm import completion

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    completion = None


class DataExtractor:
    def __init__(
        self,
        api_key=None,
        temp_dir="temp",
        output_dir="output",
        model_name=None,
        enable_cache=True,
    ):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = temp_dir
        self.output_dir = output_dir
        self.extraction_codes_dir = os.path.join(temp_dir, "extraction_codes")
        self.enable_cache = enable_cache
        self.api_key = api_key

        # Create directories
        os.makedirs(self.extraction_codes_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize code cache
        if self.enable_cache:
            cache_db_path = os.path.join(temp_dir, "extraction_cache.db")
            cache_dir = os.path.join(temp_dir, "cache")
            self.code_cache = CodeCache(
                db_path=cache_db_path, cache_dir=cache_dir
            )
            self.logger.info("Code caching enabled")
        else:
            self.code_cache = None
            self.logger.info("Code caching disabled")

        # Set model name with default fallback
        self.model_name = model_name or "gemini-2.5-flash"

        # Initialize AI provider based on model name
        self._initialize_ai_provider(api_key)

        self.extraction_history = []
        self._token_calls: list = []   # accumulates ApiCallTokens per API call
        self.logger.info(
            f"Initialized DataExtractor with model: {self.model_name}"
        )

    def _initialize_ai_provider(self, api_key):
        """Initialize AI provider based on model name"""
        self.use_litellm = False

        # Check if it's a Gemini model
        if self.model_name.startswith("gemini"):
            # Use Google Gemini API directly (google-genai SDK)
            resolved_key = api_key or os.getenv("GEMINI_API_KEY")
            if not resolved_key:
                raise ValueError(
                    "Gemini API key not provided. Set GEMINI_API_KEY "
                    "environment variable or pass api_key parameter."
                )
            self.model = genai.Client(api_key=resolved_key)
            self.logger.info(
                f"Using Google Gemini API with model: {self.model_name}"
            )
        else:
            # Use LiteLLM for other providers
            if not LITELLM_AVAILABLE:
                raise ImportError(
                    "LiteLLM is required for non-Gemini models. "
                    "Install with: pip install litellm"
                )

            if not api_key:
                # For testing purposes, allow initialization without API key
                self.logger.warning(
                    "No API key provided for non-Gemini model - "
                    "some operations will fail"
                )

            self.use_litellm = True
            self.model = None  # LiteLLM doesn't use model objects
            self.logger.info(f"Using LiteLLM with model: {self.model_name}")

    def _detect_provider_from_model(self, model_name):
        """Detect AI provider from model name"""
        model_name_lower = model_name.lower()

        if model_name_lower.startswith("gemini"):
            return "gemini"
        elif (
            model_name_lower.startswith("gpt") or "openai" in model_name_lower
        ):
            return "openai"
        elif model_name_lower.startswith("claude"):
            return "anthropic"
        elif model_name_lower.startswith("llama"):
            return "ollama"
        else:
            return "unknown"

    def _generate_content_with_ai(self, prompt):
        """Generate content using appropriate AI provider"""
        if self.use_litellm:
            # Use LiteLLM for non-Gemini models
            try:
                response = completion(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=self.api_key,
                )
                tokens = extract_litellm_tokens(response, self.model_name)
                if tokens:
                    self._token_calls.append(tokens)
                return response.choices[0].message.content
            except Exception as e:
                self.logger.error(f"LiteLLM API error: {str(e)}")
                raise
        else:
            # Use Google Gemini API (google-genai SDK)
            # Strip litellm provider prefix (e.g. "gemini/gemini-2.0-flash" → "gemini-2.0-flash")
            try:
                model_id = self.model_name.split("/")[-1]
                response = self.model.models.generate_content(
                    model=model_id,
                    contents=prompt,
                )
                tokens = extract_gemini_tokens(response, model_id)
                if tokens:
                    self._token_calls.append(tokens)
                if response and response.text:
                    return response.text
                else:
                    raise Exception("No response from Gemini API")
            except Exception as e:
                self.logger.error(f"Gemini API error: {str(e)}")
                raise

    def analyze_html_structure(self, html_content):
        """Analyze HTML to understand the data structure"""
        soup = BeautifulSoup(html_content, "html.parser")

        # Get basic info about the page
        title = soup.find("title")
        title_text = title.get_text() if title else "No title"

        # Count different types of elements
        common_elements = [
            "div",
            "span",
            "p",
            "a",
            "img",
            "ul",
            "li",
            "table",
            "tr",
            "td",
        ]
        element_counts = {}
        for element in common_elements:
            count = len(soup.find_all(element))
            if count > 0:
                element_counts[element] = count

        # Look for common patterns that might indicate data
        potential_data_patterns = []

        # Check for lists
        lists = soup.find_all(["ul", "ol"])
        if lists:
            potential_data_patterns.append(f"Found {len(lists)} lists")

        # Check for tables
        tables = soup.find_all("table")
        if tables:
            potential_data_patterns.append(f"Found {len(tables)} tables")

        # Check for cards/items (common class patterns)
        card_patterns = [
            "card",
            "item",
            "post",
            "product",
            "job",
            "listing",
            "entry",
        ]
        for pattern in card_patterns:
            elements = soup.find_all(
                class_=lambda x: x and pattern in " ".join(x).lower()
            )
            if elements:
                potential_data_patterns.append(
                    f"Found {len(elements)} elements with '{pattern}' pattern"
                )

        return {
            "title": title_text,
            "element_counts": element_counts,
            "data_patterns": potential_data_patterns,
            "html_length": len(html_content),
        }

    def get_extraction_fields(self):
        """Get the current extraction fields. Override in subclasses."""
        return ["company_name", "job_title", "apply_link", "salary_range"]

    def generate_beautifulsoup_code(self, html_content, url=None, fields=None):
        """Use Gemini to generate BeautifulSoup extraction code with
        caching support"""
        # Get fields for caching (use provided fields or default)
        extraction_fields = fields or self.get_extraction_fields()

        # Check cache first if enabled
        if self.enable_cache and self.code_cache and url:
            cached_code = self.code_cache.get_cached_code(
                url, html_content, extraction_fields
            )
            if cached_code:
                self._token_calls.append(ApiCallTokens(
                    model=self.model_name,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    from_cache=True,
                ))
                return cached_code

        # Generate new code if not cached
        self.analyze_html_structure(html_content)

        # Create field descriptions for the prompt
        field_descriptions = ", ".join(extraction_fields)

        # Prepare the prompt for the AI model
        prompt = f"""
You are an expert web scraper. Analyze the following HTML content and
generate a Python function using BeautifulSoup that extracts structured data.

IMPORTANT CONTEXT: The HTML provided has been intelligently cleaned and
reduced:
- Repeated structures have been sampled (only 2 samples shown from groups
  of 3+ similar elements)
- Empty divs, scripts, styles, ads, and navigation elements have been
  removed
- The final extraction will run on the FULL original HTML with ALL items
- Your code must be designed to handle the complete dataset, not just the
  samples shown

Requirements:
1. Create a function named 'extract_data(html_content)' that takes HTML
   string as input
2. Return structured data as a JSON-serializable dictionary/list
3. Only extract the following fields: {field_descriptions}
4. Handle edge cases and missing elements gracefully using
   try-except blocks
5. Use descriptive field names in the output that match the requested fields
6. Group related data logically
7. Always return the same structure even if some fields are empty
8. Include comprehensive error handling
9. For each item/record, include all requested fields even if some
   are null/empty
10. **Design for scalability** - your selectors must work for
    hundreds/thousands of similar items
11. **Use robust selectors** that will work across all instances,
    not just the 2 samples shown
12. **Avoid hardcoded indices** - use class names, attributes, and
    structural patterns instead

Selector Best Practices:
- Use CSS selectors or find_all() methods that capture ALL matching elements
- Prefer class-based selectors over position-based ones
- Test selectors that work for recurring patterns, not just individual samples
- Use broad selectors like `soup.find_all('div', class_='item-class')`
  to catch all items
- Handle variations in HTML structure within the same element type

Error Handling Requirements:
- Wrap individual field extractions in try-except blocks
- Provide meaningful default values for missing fields
- Continue processing other items even if one fails
- Log specific errors without stopping execution

The function should follow this template:
```python
from bs4 import BeautifulSoup
import re
from datetime import datetime

def extract_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_data = []

    try:
        # Your extraction logic here
        # Make sure to extract: {field_descriptions}
        # Return consistent structure with requested fields
        return extracted_data
    except Exception as e:
        print(f"Error extracting data: {{e}}")
        return []
```

Remember: The HTML shown contains only SAMPLES of repeated elements.
Your selectors must work for ALL instances in the full HTML. Focus on patterns
and classes that will scale to the complete dataset.
Only return the Python code, no explanations.
HTML Content:
```{html_content}```
"""

        try:
            self.logger.info(
                f"Generating BeautifulSoup code with {self.model_name} "
                f"for fields: {extraction_fields}"
            )
            response_text = self._generate_content_with_ai(prompt)

            if response_text:
                # Extract Python code from the response
                code = response_text.strip()

                # Remove markdown code block markers if present
                if code.startswith("```python"):
                    code = code[9:]
                elif code.startswith("```"):
                    code = code[3:]

                if code.endswith("```"):
                    code = code[:-3]

                code = code.strip()

                # Cache the generated code if caching is enabled
                if self.enable_cache and self.code_cache and url:
                    self.code_cache.store_code(
                        url, html_content, extraction_fields, code
                    )

                self.logger.info("Successfully generated BeautifulSoup code")
                return code
            else:
                raise Exception("No response from AI API")

        except Exception as e:
            self.logger.error(f"Error generating code with AI: {str(e)}")
            raise

    def execute_extraction_code(self, code, html_content):
        """Safely execute the generated BeautifulSoup code"""
        try:
            # Create a temporary namespace for execution
            namespace = {
                "BeautifulSoup": BeautifulSoup,
                "re": __import__("re"),
                "datetime": __import__("datetime"),
                "json": __import__("json"),
                "print": print,
            }

            # Execute the code in the namespace
            exec(code, namespace)

            # Call the extract_data function
            if "extract_data" not in namespace:
                raise Exception(
                    "Generated code doesn't contain 'extract_data' function"
                )

            self.logger.info("Executing generated extraction code...")
            extracted_data = namespace["extract_data"](html_content)

            # Validate that the result is JSON serializable
            json.dumps(extracted_data)

            count = (len(extracted_data) if isinstance(extracted_data, list)
                     else 'structured')
            self.logger.info(f"Successfully extracted data with {count} items")
            return extracted_data

        except Exception as e:
            self.logger.error(f"Error executing extraction code: {str(e)}")
            raise

    def _save_extraction_code(self, url, code):
        """Save generated extraction code to temp folder"""
        try:
            if url:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace("www.", "").replace(
                    ".", "_"
                )
            else:
                domain = "unknown"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{domain}_{timestamp}_extraction_code.py"
            filepath = os.path.join(self.extraction_codes_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(
                    f"# Generated extraction code for: "
                    f"{url or 'Unknown URL'}\n"
                )
                f.write(f"# Generated at: {datetime.now().isoformat()}\n\n")
                f.write(code)

            self.logger.debug(f"Extraction code saved to: {filepath}")
            return filepath
        except Exception as e:
            self.logger.warning(f"Failed to save extraction code: {e}")
            return None

    def save_data(self, data, filename=None, url=None, format="json"):
        """Save extracted data to JSON or CSV file in the output directory

        Args:
            data: Extracted data (list of dictionaries or dictionary)
            filename: Output filename (optional)
            url: Source URL (optional)
            format: Output format - 'json' (default) or 'csv'
        """
        if not filename:
            if url:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace("www.", "").replace(
                    ".", "_"
                )
            else:
                domain = "unknown"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = "json" if format.lower() == "json" else "csv"
            filename = f"{domain}_{timestamp}.{extension}"

        # Ensure filename goes to output directory
        if not os.path.dirname(filename):
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = filename

        try:
            if format.lower() == "csv":
                self._save_as_csv(data, filepath, url)
            else:
                self._save_as_json(data, filepath, url)

            self.logger.info(f"Data saved to: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Error saving data to {filepath}: {str(e)}")
            raise

    def _save_as_json(self, data, filepath, url):
        """Save data as JSON file"""
        output_data = {
            "extraction_info": {
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "total_items": len(data) if isinstance(data, list) else 1,
                "format": "json",
            },
            "data": data,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

    def _save_as_csv(self, data, filepath, url):
        """Save data as CSV file"""
        if not data:
            raise ValueError("No data to save to CSV")

        # Convert single item to list for consistent processing
        if isinstance(data, dict):
            data_list = [data]
        else:
            data_list = data

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

    def extract_and_save(
        self, html_content, url=None, output_file=None, format="json"
    ):
        """
        Main method to extract data from HTML and save to file

        Args:
            html_content: HTML content to extract data from
            url: Source URL (optional)
            output_file: Output filename (optional)
            format: Output format - 'json' (default) or 'csv'
        """
        try:
            self.logger.info("Starting data extraction process...")

            # Generate BeautifulSoup code using Gemini
            extraction_code = self.generate_beautifulsoup_code(
                html_content, url
            )

            # Store the generated code for debugging
            code_info = {
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "code": extraction_code,
            }
            self.extraction_history.append(code_info)

            # Execute the generated code
            extracted_data = self.execute_extraction_code(
                extraction_code, html_content
            )

            # Save the data
            output_filename = self.save_data(
                extracted_data, output_file, url, format
            )

            # Save the generated code to temp folder
            code_filename = self._save_extraction_code(url, extraction_code)

            self.logger.info(
                f"Extraction completed. Data: {output_filename}, "
                f"Code: {code_filename}"
            )

            return {
                "success": True,
                "data_file": output_filename,
                "code_file": code_filename,
                "extracted_items": (
                    len(extracted_data)
                    if isinstance(extracted_data, list)
                    else 1
                ),
                "extraction_code": extraction_code,
                "format": format,
            }

        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "extraction_code": getattr(self, "last_generated_code", None),
            }

    def get_token_usage(self) -> dict:
        """Return aggregated token usage across all API calls made so far."""
        return summarise(self._token_calls)

    def get_cache_stats(self):
        """Get cache statistics if caching is enabled"""
        if self.enable_cache and self.code_cache:
            return self.code_cache.get_cache_stats()
        else:
            return {"message": "Caching is disabled"}

    def clear_cache(self):
        """Clear the code cache if caching is enabled"""
        if self.enable_cache and self.code_cache:
            return self.code_cache.clear_cache()
        else:
            self.logger.info("Caching is disabled - nothing to clear")
            return False

    def cleanup_old_cache(self, days_old=30):
        """Clean up old cache entries if caching is enabled"""
        if self.enable_cache and self.code_cache:
            return self.code_cache.cleanup_old_entries(days_old)
        else:
            self.logger.info("Caching is disabled - nothing to cleanup")
            return 0

    def extract_data(self, html_content, url=None, fields=None):
        """Extract data using generated code with caching support"""
        try:
            # Generate code with current fields (with caching)
            extraction_code = self.generate_beautifulsoup_code(
                html_content, url, fields
            )

            # Execute the code
            extracted_data = self.execute_extraction_code(
                extraction_code, html_content
            )

            return extracted_data

        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            raise

    def extract_data_with_separation(
        self, cleaned_html, original_html, url=None, fields=None
    ):
        """
        Extract data using cleaned HTML for code generation and
        original HTML for execution.

        Args:
            cleaned_html: Cleaned HTML used for AI code generation
                          (reduced size)
            original_html: Original HTML used for data extraction
                           (complete data)
            url: URL for caching and logging
            fields: Fields to extract

        Returns:
            Extracted data list
        """
        try:
            self.logger.info(
                "Using HTML separation: cleaned for code generation, "
                "original for execution"
            )

            # Generate code using cleaned HTML (smaller, focused for AI)
            extraction_code = self.generate_beautifulsoup_code(
                cleaned_html, url, fields
            )

            # Execute the code on original HTML (complete data)
            extracted_data = self.execute_extraction_code(
                extraction_code, original_html
            )

            return extracted_data

        except Exception as e:
            self.logger.error(
                f"Data extraction with separation failed: {str(e)}"
            )
            raise
