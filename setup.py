"""
Setup script for Universal Scraper package
"""

from setuptools import setup, find_packages
import os

# Get version from the package
def get_version():
    """Get version from universal_scraper/__init__.py"""
    version_file = os.path.join(os.path.dirname(__file__), 'universal_scraper', '__init__.py')
    with open(version_file, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"').strip("'")
    raise RuntimeError('Unable to find version string.')

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
try:
    with open(
        os.path.join(this_directory, "README.md"), encoding="utf-8"
    ) as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = """
    Universal Scraper - AI-powered web scraping with customizable
    field extraction

    A Python module that uses AI to automatically extract structured data
    from web pages
    with user-defined fields and JSON output.
    """

setup(
    name="universal-scraper",
    version=get_version(),
    author="Witeso",
    author_email="support@witeso.com",
    description=(
        "AI-powered web scraping with customizable field extraction "
        "using multiple AI providers"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pushpenderindia/universal-scraper",
    packages=find_packages(),
    py_modules=["main"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup :: HTML",
    ],
    python_requires=">=3.9",
    install_requires=[
        "google-genai>=1.0.0",
        "litellm>=1.70.0",
        "beautifulsoup4>=4.11.0",
        "requests>=2.28.0",
        "selenium>=4.0.0",
        "lxml>=4.9.0",
        "fake-useragent>=1.2.0",
        "cloudscraper>=1.2.0",
        "flask>=2.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "mcp": [
            "mcp>=1.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "universal-scraper=main:main",
            "universal-scraper-mcp=universal_scraper.mcp_server:main_sync",
            "universal-scraper-ui=universal_scraper.web_ui:main",
        ],
    },
    keywords=[
        "web scraping",
        "ai",
        "data extraction",
        "beautifulsoup",
        "gemini",
        "openai",
        "anthropic",
        "claude",
        "gpt",
        "litellm",
        "automation",
        "html parsing",
        "structured data",
        "caching",
        "performance",
        "multi-provider",
        "mcp",
        "model context protocol",
    ],
    project_urls={
        "Bug Reports": "https://github.com/pushpenderindia/universal-scraper/issues",
        "Source": "https://github.com/pushpenderindia/universal-scraper",
        "Documentation": "https://github.com/pushpenderindia/universal-scraper/wiki",
    },
)
