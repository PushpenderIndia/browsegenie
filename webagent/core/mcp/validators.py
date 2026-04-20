"""
Input validation utilities for the MCP server.

This module provides validation classes and functions for MCP server inputs.
"""

from typing import List
from urllib.parse import urlparse
from .exceptions import ValidationError


class URLValidator:
    """Validator class for URL inputs."""

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: The URL string to validate

        Returns:
            True if URL is valid

        Raises:
            ValidationError: If URL format is invalid
        """
        if not url:
            raise ValidationError("URL is required")

        if not isinstance(url, str):
            raise ValidationError("URL must be a string")

        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValidationError(f"Invalid URL format: {url}")

            if parsed.scheme not in ["http", "https"]:
                raise ValidationError(f"URL must use http or https protocol: {url}")

            return True
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"URL validation failed: {str(e)}")

    @staticmethod
    def validate_urls(urls: List[str]) -> bool:
        """
        Validate a list of URLs.

        Args:
            urls: List of URL strings to validate

        Returns:
            True if all URLs are valid

        Raises:
            ValidationError: If any URL is invalid
        """
        if not urls:
            raise ValidationError("URLs list is required")

        if not isinstance(urls, list):
            raise ValidationError("URLs must be provided as a list")

        invalid_urls = []
        for url in urls:
            try:
                URLValidator.validate_url(url)
            except ValidationError:
                invalid_urls.append(url)

        if invalid_urls:
            raise ValidationError(f"Invalid URLs found: {invalid_urls}")

        return True


class FieldValidator:
    """Validator class for field inputs."""

    @staticmethod
    def validate_fields(fields: List[str]) -> bool:
        """
        Validate extraction fields.

        Args:
            fields: List of field names to validate

        Returns:
            True if fields are valid

        Raises:
            ValidationError: If fields are invalid
        """
        if fields is None:
            return True

        if not isinstance(fields, list):
            raise ValidationError("Fields must be provided as a list")

        if not all(isinstance(field, str) for field in fields):
            raise ValidationError("All fields must be strings")

        if len(fields) == 0:
            return True

        if len(set(fields)) != len(fields):
            raise ValidationError("Duplicate fields are not allowed")

        return True


class FormatValidator:
    """Validator class for output format inputs."""

    VALID_FORMATS = ["json", "csv"]

    @staticmethod
    def validate_format(format_type: str) -> bool:
        """
        Validate output format.

        Args:
            format_type: The output format to validate

        Returns:
            True if format is valid

        Raises:
            ValidationError: If format is invalid
        """
        if format_type not in FormatValidator.VALID_FORMATS:
            raise ValidationError(
                f"Invalid format: {format_type}. "
                f"Must be one of: {', '.join(FormatValidator.VALID_FORMATS)}"
            )

        return True
