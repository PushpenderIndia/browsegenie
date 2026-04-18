<h1 align="center"> Universal Scraper</h1>

<h2 align="center"> The Python package for scraping data from any website</h2>

<p align="center">
<a href="https://www.codefactor.io/repository/github/pushpenderindia/universal-scraper"><img alt="pypi" src="https://www.codefactor.io/repository/github/pushpenderindia/universal-scraper/badge"></a>  
<a href="https://socket.dev/pypi/package/universal-scraper/overview"><img alt="pypi" src="https://socket.dev/api/badge/pypi/package/universal-scraper/latest?artifact_id=tar-gz"></a>
<img alt="CodeQL Status" src="https://github.com/pushpenderindia/universal-scraper/actions/workflows/codeql-analysis.yml/badge.svg">
<a href="https://codecov.io/gh/pushpenderindia/universal-scraper"><img alt="codecov" src="https://codecov.io/gh/pushpenderindia/universal-scraper/branch/main/graph/badge.svg"></a>
<a href="https://pypi.org/project/universal-scraper/"><img alt="pypi" src="https://img.shields.io/pypi/v/universal-scraper.svg"></a>
<a href="https://pepy.tech/project/universal-scraper?versions=1*&versions=2*&versions=3*"><img alt="Downloads" src="https://pepy.tech/badge/universal-scraper"></a>
<a href="https://pepy.tech/project/universal-scraper?versions=1*&versions=2*&versions=3*"><img alt="Downloads" src="https://pepy.tech/badge/universal-scraper/month"></a>
<a href="https://github.com/pushpenderindia/universal-scraper/commits/main"><img alt="GitHub lastest commit" src="https://img.shields.io/github/last-commit/pushpenderindia/universal-scraper?color=blue&style=flat-square"></a>
<a href="#"><img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/universal-scraper?style=flat-square"></a>
</p>

## Table of Contents

- [Web UI — No-Code Mode](#web-ui--no-code-mode)
- [How Universal Scraper Works](#how-universal-scraper-works)
- [Live Working Example](#live-working-example)
- [How It Works](#how-it-works)
- [Smart HTML Cleaner](#smart-html-cleaner)
- [Installation (Recommended)](#installation-recommended)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [1. Set up your API key](#1-set-up-your-api-key)
  - [2. Basic Usage](#2-basic-usage)
  - [3. Convenience Function](#3-convenience-function)
- [Export Formats](#export-formats)
- [CLI Usage](#cli-usage)
- [MCP Server Usage](#mcp-server-usage)
- [Cache Management](#cache-management)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)
- [Output Format](#output-format)
- [Common Field Examples](#common-field-examples)
- [Multi-Provider AI Support](#multi-provider-ai-support)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributors](#contributors)
- [Contributing](#contributing)
- [License](#license)
- [Changelog](#changelog)

--------------------------------------------------------------------------

## Web UI — No-Code Mode

The fastest way to use Universal Scraper — no Python required. Install the package and launch the local web UI with one command:

```bash
pip install universal-scraper
universal-scraper-ui
```

Your browser opens automatically at `http://127.0.0.1:5000`.

![Universal Scraper Web UI](docs/local_website.png)

### What you can do in the UI

| Feature | Details |
|---------|---------|
| **Provider & Model** | Select Google Gemini, OpenAI, Anthropic, or Ollama. Models are fetched **live** from the provider's API when you enter a key — always current, never hardcoded. Falls back to 1,700+ LiteLLM models when no key is entered. Only text/chat models are listed. |
| **API Key auto-fill** | `GEMINI_API_KEY`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` environment variables are pre-filled on page load. |
| **Extraction fields** | Add fields as interactive chips (`product_name`, `price`, `rating` …). Press Enter or comma to add; click × to remove. |
| **Output formats** | **JSON** → syntax-highlighted result. **CSV** → rendered as an HTML table in the browser; download exports a proper `.csv` file. |
| **Real-time logs** | Live terminal-style stream (Server-Sent Events) showing every internal step — fetch, clean, AI call, cache hit — as the scrape runs. |
| **Token usage** | After each scrape a token bar shows total tokens used, prompt/completion split, and cache-hit count. Click **Breakdown →** for a per-API-call modal. |

### CLI options

```bash
universal-scraper-ui --port 8080        # custom port
universal-scraper-ui --host 0.0.0.0    # bind to all interfaces
universal-scraper-ui --no-browser      # skip auto-opening the browser
```

--------------------------------------------------------------------------

A Python module for AI-powered web scraping with customizable field extraction using multiple AI providers (Gemini, OpenAI, Anthropic, and more via LiteLLM).

Automatically Generates Scraper Code, Only If Page Structure is changed, Otherwise use the same previously generated code

## Motivation for This Module

- Traditionally, Developers have to write the Web Scraper manually using technologies such as `requests/cloudscraper/selenium` (in `Python`) or `Axios/Cheerio/Puppeteer/selenium` (in `JS`)
- We need to write BeautifulSoup4 selectors using xpath/class/id etc, by analysing the HTML
- Even slight change in HTML structure breaks the scrapers, this fragility means scrapers require constant, time-consuming maintenance and frequent rewrites to remain functional
- Writing end to end web scrapers from fetching HTML to Parsing it and then exporting that data in JSON or CSV is time consuming
- How about a module, which can write BeautifulSoup4 code on the fly by Analysing 98%+ less sized HTML structure, then use that extraction code for subsequent pages who have same HTML structure
- A module which only regenerates the Beautifulsoup4 code, only if the HTML structure is changed
- A module which can do couple of hours of web scraping task in just 5 seconds and still `costing less than 0.7 cents` (~$0.00786) on LLM API Calls (`only for generating Scraper code`)

## How Universal Scraper Works

```mermaid
graph TB
    A[🌐 Input URL] --> B[📥 HTML Fetcher]
    B --> B1[CloudScraper Anti-Bot Protection]
    B1 --> C[🧹 Smart HTML Cleaner]
    
    C --> C1[Remove Scripts & Styles]
    C1 --> C2[Remove Ads & Analytics]
    C2 --> C2a[Remove Inline SVG Images]
    C2a --> C2aa[Replace URLs with Placeholders]
    C2aa --> C2b[Remove Non-Essential HTML Attributes]
    C2b --> C3[Remove Navigation Elements]
    C3 --> C4[Detect Repeating Structures]
    C4 --> C5[Keep 2 Samples, Remove Others]
    C5 --> C6[Remove Empty Divs]
    C6 --> D[📊 98% Size Reduction]
    
    D --> D1[🔗 Generate Structural Hash]
    D1 --> E{🔍 Check Code Cache}
    E -->|Cache Hit & Hash Match| F[♻️ Use Cached Code]
    E -->|Cache Miss or Hash Changed| E1[🗑️ Discard Old Cache]
    E1 --> G[🤖 AI Code Generation]
    
    G --> G1[🧠 Choose AI Provider]
    G1 --> G2[Gemini 2.5-Flash Default]
    G1 --> G3[OpenAI GPT-4/GPT-4o]
    G1 --> G4[Claude 3 Opus/Sonnet/Haiku]
    G1 --> G5[100+ Other Models via LiteLLM]
    
    G2 --> H[📝 Generate BeautifulSoup Code]
    G3 --> H
    G4 --> H
    G5 --> H
    
    H --> I[💾 Cache Generated Code + Hash]
    F --> J[⚡ Execute Code on Original HTML]
    I --> J
    
    J --> K[📋 Extract Structured Data]
    K --> L{📁 Output Format}
    L -->|JSON| M[💾 Save as JSON]
    L -->|CSV| N[📊 Save as CSV]
    
    M --> O[✅ Complete with Metadata]
    N --> O
    
    style A fill:#e1f5fe
    style D fill:#4caf50,color:#fff
    style D1 fill:#ff5722,color:#fff
    style E fill:#ff9800,color:#fff
    style E1 fill:#f44336,color:#fff
    style F fill:#4caf50,color:#fff
    style G1 fill:#9c27b0,color:#fff
    style O fill:#2196f3,color:#fff
```

**Key Performance Benefits:**
- **98% HTML Size Reduction** → Massive token savings
- **Smart Caching** → 90%+ API cost reduction on repeat scraping  
- **Multi-Provider Support** → Choose the best AI for your use case, 100+ LLMs supported
- **Dual HTML Processing** → Clean HTML and reduces HTML size upto 98.3%+ for AI analysis, original HTML for complete data extraction
- **Generates BeautifulSoup4 code on the fly** → Generates structural hash of HTML page, so that it reuse extraction code on repeat scraping

**Token Count Comparison (Claude Sonnet 4):**

- 2,619 tokens: ~$0.00786 (0.8 cents)
- 150,742 tokens: ~$0.45 (45 cents)
- Token ratio: 150,742 ÷ 2,619 = **57.5x more tokens**
- Saving: The larger request costs **57.5x** more than the smaller one

## Live Working Example

Here's a real working example showing Universal Scraper in action with Gemini 2.5 Pro:

```python
>>> from universal_scraper import UniversalScraper
>>> scraper = UniversalScraper(api_key="AIzxxxxxxxxxxxxxxxxxxxxx", model_name="gemini-2.5-pro")
2025-09-17 01:22:30 - code_cache - INFO - CodeCache initialized with database: temp/extraction_cache.db
2025-09-17 01:22:30 - data_extractor - INFO - Code caching enabled
2025-09-17 01:22:30 - data_extractor - INFO - Using Google Gemini API with model: gemini-2.5-pro
2025-09-17 01:22:30 - data_extractor - INFO - Initialized DataExtractor with model: gemini-2.5-pro

>>> # Set fields for e-commerce laptop scraping
>>> scraper.set_fields(["product_name", "product_price", "product_rating", "product_description", "availability"])
2025-09-17 01:22:31 - universal_scraper - INFO - Extraction fields updated: ['product_name', 'product_price', 'product_rating', 'product_description', 'availability']

>>> result = scraper.scrape_url("https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops", save_to_file=True, format='csv')
2025-09-17 01:22:33 - universal_scraper.scraper - INFO - Starting scraping for: https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops
2025-09-17 01:22:33 - universal_scraper.core.html_fetcher - INFO - Starting to fetch HTML for: https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops
2025-09-17 01:22:33 - universal_scraper.core.html_fetcher - INFO - Fetching https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops with cloudscraper...
2025-09-17 01:22:33 - universal_scraper.core.html_fetcher - INFO - Successfully fetched content with cloudscraper. Length: 163496
2025-09-17 01:22:33 - universal_scraper.core.html_fetcher - INFO - Successfully fetched HTML with cloudscraper
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Starting HTML cleaning process...
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed noise. Length: 142614
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed SVG/images. Length: 142614
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Replaced 252 URL sources with placeholders.
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Replaced URL sources. Length: 133928
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed iframes. Length: 133928
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed headers/footers. Length: 127879
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Focused on main content. Length: 127642
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Limited select options. Length: 127642
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed 3 empty div elements in 1 iterations
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed empty divs. Length: 127553
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Collapsed 117 long text nodes
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Collapsed long text nodes. Length: 123068
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed 0 non-essential attributes (3560 → 3560)
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed non-essential attributes. Length: 123068
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed whitespace between tags. Length: 123068 → 118089 (4.0% reduction)
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Found 117 similar structures, keeping 2, removing 115
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Found 117 similar structures, keeping 2, removing 115
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Found 117 similar structures, keeping 2, removing 115
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Found 117 similar structures, keeping 2, removing 115
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed 115 repeating structure elements
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed repeating structures. Length: 2371
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed 0 empty div elements in 0 iterations
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Removed empty divs (post-compression). Length: 2371
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - HTML cleaning completed. Original: 150742, Final: 2371
2025-09-17 01:22:33 - universal_scraper.core.cleaning.base_cleaner - INFO - Reduction: 98.4%
2025-09-17 01:22:33 - data_extractor - INFO - Using HTML separation: cleaned for code generation, original for execution
2025-09-17 01:22:33 - code_cache - INFO - Cache MISS for https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops
2025-09-17 01:22:33 - data_extractor - INFO - Generating BeautifulSoup code with gemini-2.5-pro for fields: ['product_name', 'product_price', 'product_rating', 'product_description', 'availability']
2025-09-17 01:22:37 - code_cache - INFO - Code cached for https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops (hash: bd0ed6e62683fcfb...)
2025-09-17 01:22:37 - data_extractor - INFO - Successfully generated BeautifulSoup code
2025-09-17 01:22:37 - data_extractor - INFO - Executing generated extraction code...
2025-09-17 01:22:37 - data_extractor - INFO - Successfully extracted data with 117 items
2025-09-17 01:22:37 - universal_scraper - INFO - Successfully extracted data from https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops
>>>

# ✨ Results: 117 laptop products extracted from 163KB HTML in ~5 seconds!
# 🎯 98.4% HTML size reduction (163KB → 2.3KB for AI processing to generate BeautifulSoup4 code)  
# 💾 Data automatically saved as CSV with product_name, product_price, product_rating, etc.
```

**What Just Happened:**
1. **Fields Configured** for e-commerce: product_name, product_price, product_rating, etc.
2. **HTML Fetched** with anti-bot protection (163KB)
3. **Smart Cleaning** reduced size by 98.4% (163KB → 2.3KB)
4. **AI Generated** custom extraction code using GPT-4o for specified fields
5. **Code Cached** for future use (90% cost savings on re-runs)
6. **117 Laptop Products Extracted** from original HTML with complete data
7. **Saved as CSV** ready for analysis with all specified product fields

## How It Works

1. **HTML Fetching**: Uses cloudscraper or selenium to fetch HTML content, handling anti-bot measures
2. **Smart HTML Cleaning**: Removes 98%+ of noise (scripts, ads, navigation, repeated structures, empty divs) while preserving data structure
3. **Structure-Based Caching**: Creates structural hash and checks cache for existing extraction code
4. **AI Code Generation**: Uses your chosen AI provider (Gemini, OpenAI, Claude, etc.) to generate custom BeautifulSoup code on cleaned HTML (only when not cached)
5. **Code Execution**: Runs the cached/generated code on original HTML to extract ALL data items
6. **Export Output data as Json/CSV**: Returns complete, consistent, structured data with metadata and performance stats

## Smart HTML Cleaner

### What Gets Removed
- **Scripts & Styles**: JavaScript, CSS, and style blocks
- **Ads & Analytics**: Advertisement content and tracking scripts
- **Navigation**: Headers, footers, sidebars, and menu elements
- **Metadata**: Meta tags, SEO tags, and hidden elements
- **Empty Elements**: Recursively removes empty div elements that don't contain meaningful content
- **Noise**: Comments, unnecessary attributes, and whitespace
- **Inline SVG Image**: Makes the page size bulky
- **URL Placeholders**: Replaces long URLs (src, href, action) with short placeholders like [IMG_URL], [LINK_URL] to reduce token count
- **Non Essential Attributes Remover**: It Distinguishes between essential attributes (id, class, href, data-price) and non-essential ones (style, onclick, data-analytics)
- **Whitespace & Blank Lines Remover**: It Compresses the final HTML, before sending it to LLM for analysis

### Repeating Structure Reduction
The cleaner intelligently detects and reduces repeated HTML structures:

- **Pattern Detection**: Uses structural hashing + similarity algorithms to find repeated elements
- **Smart Sampling**: Keeps 2 samples from groups of 3+ similar structures (e.g., 20 job cards → 2 samples)
- **Structure Preservation**: Maintains document flow and parent-child relationships
- **AI Optimization**: Provides enough samples for pattern recognition without overwhelming the AI

### Empty Element Removal
The cleaner intelligently removes empty div elements:

- **Recursive Processing**: Starts from innermost divs and works outward
- **Content Detection**: Preserves divs with text, images, inputs, or interactive elements
- **Structure Preservation**: Maintains parent-child relationships and avoids breaking important structural elements
- **Smart Analysis**: Removes placeholder/skeleton divs while keeping functional containers

**Example**: Removes empty animation placeholders like `<div class="animate-pulse"></div>` while preserving divs containing actual content.

## Installation (Recommended)

```
pip install universal-scraper
```

## Installation (Global level on Mac)

```
brew install pipx
sudo pipx install "universal-scraper[mcp]" --global
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Universal_Scrapper
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   Or install manually:
   ```bash
   pip install google-genai beautifulsoup4 requests selenium lxml fake-useragent flask
   ```

3. **Install the module**:
   ```bash
   pip install -e .
   ```

## Quick Start

### 1. Set up your API key

**Option A: Use Gemini (Default - Recommended)**
Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey):

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

**Option B: Use OpenAI**
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

**Option C: Use Anthropic Claude**
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
```

**Option D: Pass API key directly**
```python
# For any provider - just pass the API key directly
scraper = UniversalScraper(api_key="your_api_key")
```

### 2. Basic Usage

```python
from universal_scraper import UniversalScraper

# Option 1: Auto-detect provider (uses Gemini by default)
scraper = UniversalScraper(api_key="your_gemini_api_key")

# Option 2: Specify Gemini model explicitly
scraper = UniversalScraper(api_key="your_gemini_api_key", model_name="gemini-2.5-flash")

# Option 3: Use OpenAI
scraper = UniversalScraper(api_key="your_openai_api_key", model_name="gpt-4")

# Option 4: Use Anthropic Claude
scraper = UniversalScraper(api_key="your_anthropic_api_key", model_name="claude-3-sonnet-20240229")

# Option 5: Use any other provider supported by LiteLLM
scraper = UniversalScraper(api_key="your_api_key", model_name="llama-2-70b-chat")

# Set the fields you want to extract
scraper.set_fields([
    "company_name", 
    "job_title", 
    "apply_link", 
    "salary_range",
    "location"
])

# Check current model
print(f"Using model: {scraper.get_model_name()}")

# Scrape a URL (default JSON format)
result = scraper.scrape_url("https://example.com/jobs", save_to_file=True)

print(f"Extracted {result['metadata']['items_extracted']} items")
print(f"Data saved to: {result.get('saved_to')}")

# Scrape and save as CSV
result = scraper.scrape_url("https://example.com/jobs", save_to_file=True, format='csv')
print(f"CSV data saved to: {result.get('saved_to')}")
```

### 3. Convenience Function

For quick one-off scraping:

```python
from universal_scraper import scrape

# Quick scraping with default JSON format
data = scrape(
    url="https://example.com/jobs",
    api_key="your_gemini_api_key",
    fields=["company_name", "job_title", "apply_link"]
)

# Quick scraping with CSV format
data = scrape(
    url="https://example.com/jobs",
    api_key="your_gemini_api_key",
    fields=["company_name", "job_title", "apply_link"],
    format="csv"
)

# Quick scraping with OpenAI
data = scrape(
    url="https://example.com/jobs",
    api_key="your_openai_api_key",
    fields=["company_name", "job_title", "apply_link"],
    model_name="gpt-4"
)

# Quick scraping with Anthropic Claude
data = scrape(
    url="https://example.com/jobs",
    api_key="your_anthropic_api_key",
    fields=["company_name", "job_title", "apply_link"],
    model_name="claude-3-haiku-20240307"
)

print(data['data'])  # The extracted data
```

## Export Formats

Universal Scraper supports multiple output formats to suit your data processing needs:

### JSON Export (Default)
```python
# JSON is the default format
result = scraper.scrape_url("https://example.com/jobs", save_to_file=True)
# or explicitly specify
result = scraper.scrape_url("https://example.com/jobs", save_to_file=True, format='json')
```

**JSON Output Structure:**
```json
{
  "url": "https://example.com",
  "timestamp": "2025-01-01T12:00:00",
  "fields": ["company_name", "job_title", "apply_link"],
  "data": [
    {
      "company_name": "Example Corp",
      "job_title": "Software Engineer", 
      "apply_link": "https://example.com/apply/123"
    }
  ],
  "metadata": {
    "raw_html_length": 50000,
    "cleaned_html_length": 15000,
    "items_extracted": 1
  }
}
```

### CSV Export
```python
# Export as CSV for spreadsheet analysis
result = scraper.scrape_url("https://example.com/jobs", save_to_file=True, format='csv')
```

**CSV Output:**
- Clean tabular format with headers
- All fields as columns, missing values filled with empty strings
- Perfect for Excel, Google Sheets, or pandas processing
- Automatically handles varying field structures across items

### Multiple URLs with Format Choice
```python
urls = ["https://site1.com", "https://site2.com", "https://site3.com"]

# Save all as JSON (default)
results = scraper.scrape_multiple_urls(urls, save_to_files=True)

# Save all as CSV
results = scraper.scrape_multiple_urls(urls, save_to_files=True, format='csv')
```

### CLI Usage

```bash
# Gemini (default) - auto-detects from environment
universal-scraper https://example.com/jobs --output jobs.json

# OpenAI GPT models
universal-scraper https://example.com/products --api-key YOUR_OPENAI_KEY --model gpt-4 --format csv

# Anthropic Claude models  
universal-scraper https://example.com/data --api-key YOUR_ANTHROPIC_KEY --model claude-3-haiku-20240307

# Custom fields extraction
universal-scraper https://example.com/listings --fields product_name product_price product_rating

# Batch processing multiple URLs
universal-scraper --urls urls.txt --output-dir results --format csv --model gpt-4o-mini

# Verbose logging with any provider
universal-scraper https://example.com --api-key YOUR_KEY --model gpt-4 --verbose
```

**🔧 Advanced CLI Options:**
```bash
# Set custom extraction fields
universal-scraper URL --fields title price description availability

# Use environment variables (auto-detected)
export OPENAI_API_KEY="your_key"
universal-scraper URL --model gpt-4

# Multiple output formats
universal-scraper URL --format json    # Default
universal-scraper URL --format csv     # Spreadsheet-ready

# Batch processing
echo -e "https://site1.com\nhttps://site2.com" > urls.txt
universal-scraper --urls urls.txt --output-dir batch_results
```

**🔗 Provider Support**: All 100+ models supported by LiteLLM work in CLI! See [LiteLLM Providers](https://docs.litellm.ai/docs/providers) for complete list.

**Development Usage** (from cloned repo):
```bash
python main.py https://example.com/jobs --api-key YOUR_KEY --model gpt-4
```

## MCP Server Usage

Universal Scraper works as an MCP (Model Context Protocol) server, allowing AI assistants to scrape websites directly.

### Quick Setup

1. **Install with MCP support:**
```bash
pip install universal-scraper
```

2. **Set your AI API key:**
```bash
export GEMINI_API_KEY="your_key"  # or OPENAI_API_KEY, ANTHROPIC_API_KEY
```

### Claude Code Setup

Add this to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "universal-scraper": {
      "command": "universal-scraper-mcp"
    }
  }
}
```

or Run this command in your terminal

```
claude mcp add universal-scraper universal-scraper-mcp
```

![](docs/claude_code_integration.png)

### Cursor Setup

Add this to your Cursor MCP configuration:

```json
{
  "mcpServers": {
    "universal-scraper": {
      "command": "universal-scraper-mcp"
    }
  }
}
```

### Available Tools

- **scrape_url**: Scrape a single URL
- **scrape_multiple_urls**: Scrape multiple URLs
- **configure_scraper**: Set API keys and models
- **get_scraper_info**: Check current settings
- **clear_cache**: Clear cached data

### Example Usage

Once configured, just ask your AI assistant:

> "Scrape https://news.ycombinator.com and extract the top story titles and links"

> "Scrape this product page and get the price, name, and reviews"

## Cache Management
```python
scraper = UniversalScraper(api_key="your_key")

# View cache statistics
stats = scraper.get_cache_stats()
print(f"Cached entries: {stats['total_entries']}")
print(f"Total cache hits: {stats['total_uses']}")

# Clear old entries (30+ days)
removed = scraper.cleanup_old_cache(30)
print(f"Removed {removed} old entries")

# Clear entire cache
scraper.clear_cache()

# Disable/enable caching
scraper.disable_cache()  # For testing
scraper.enable_cache()   # Re-enable
```

## Advanced Usage

### Multiple URLs

```python
scraper = UniversalScraper(api_key="your_api_key")
scraper.set_fields(["title", "price", "description"])

urls = [
    "https://site1.com/products",
    "https://site2.com/items", 
    "https://site3.com/listings"
]

# Scrape all URLs and save as JSON (default)
results = scraper.scrape_multiple_urls(urls, save_to_files=True)

# Scrape all URLs and save as CSV for analysis
results = scraper.scrape_multiple_urls(urls, save_to_files=True, format='csv')

for result in results:
    if result.get('error'):
        print(f"Failed {result['url']}: {result['error']}")
    else:
        print(f"Success {result['url']}: {result['metadata']['items_extracted']} items")
```

### Custom Configuration

```python
scraper = UniversalScraper(
    api_key="your_api_key",
    temp_dir="custom_temp",      # Custom temporary directory
    output_dir="custom_output",  # Custom output directory  
    log_level=logging.DEBUG,     # Enable debug logging
    model_name="gpt-4"           # Custom model (OpenAI, Gemini, Claude, etc.)
)

# Configure for e-commerce scraping
scraper.set_fields([
    "product_name",
    "product_price", 
    "product_rating",
    "product_reviews_count",
    "product_availability",
    "product_description"
])

# Check and change model dynamically
print(f"Current model: {scraper.get_model_name()}")
scraper.set_model_name("gpt-4")  # Switch to OpenAI
print(f"Switched to: {scraper.get_model_name()}")

# Or switch to Claude
scraper.set_model_name("claude-3-sonnet-20240229")
print(f"Switched to: {scraper.get_model_name()}")

result = scraper.scrape_url("https://ecommerce-site.com", save_to_file=True)
```

## API Reference

### UniversalScraper Class

#### Constructor
```python
UniversalScraper(api_key=None, temp_dir="temp", output_dir="output", log_level=logging.INFO, model_name=None)
```

- `api_key`: AI provider API key (auto-detects provider, or set specific env vars)
- `temp_dir`: Directory for temporary files
- `output_dir`: Directory for output files
- `log_level`: Logging level
- `model_name`: AI model name (default: 'gemini-2.5-flash', supports 100+ models via LiteLLM)
  - See [LiteLLM Providers](https://docs.litellm.ai/docs/providers) for complete model list and setup

#### Methods

- `set_fields(fields: List[str])`: Set the fields to extract
- `get_fields() -> List[str]`: Get current fields configuration
- `get_model_name() -> str`: Get current Gemini model name
- `set_model_name(model_name: str)`: Change the Gemini model
- `scrape_url(url: str, save_to_file=False, output_filename=None, format='json') -> Dict`: Scrape a single URL
- `scrape_multiple_urls(urls: List[str], save_to_files=True, format='json') -> List[Dict]`: Scrape multiple URLs

### Convenience Function

```python
scrape(url: str, api_key: str, fields: List[str], model_name: Optional[str] = None, format: str = 'json') -> Dict
```

Quick scraping function for simple use cases. Auto-detects AI provider from API key pattern.

**Note**: For model names and provider-specific setup, refer to the [LiteLLM Providers Documentation](https://docs.litellm.ai/docs/providers).

## Output Format

The scraped data is returned in a structured format:

```json
{
  "url": "https://example.com",
  "timestamp": "2025-01-01T12:00:00",
  "fields": ["company_name", "job_title", "apply_link"],
  "data": [
    {
      "company_name": "Example Corp",
      "job_title": "Software Engineer", 
      "apply_link": "https://example.com/apply/123"
    }
  ],
  "metadata": {
    "raw_html_length": 50000,
    "cleaned_html_length": 15000,
    "items_extracted": 1
  }
}
```

## Common Field Examples

### Job Listings
```python
scraper.set_fields([
    "company_name",
    "job_title", 
    "apply_link",
    "salary_range",
    "location",
    "job_description",
    "employment_type",
    "experience_level"
])
```

### E-commerce Products
```python
scraper.set_fields([
    "product_name",
    "product_price",
    "product_rating", 
    "product_reviews_count",
    "product_availability",
    "product_image_url",
    "product_description"
])
```

### News Articles
```python
scraper.set_fields([
    "article_title",
    "article_content",
    "article_author",
    "publish_date", 
    "article_url",
    "article_category"
])
```

## Multi-Provider AI Support

Universal Scraper now supports multiple AI providers through LiteLLM integration:

### Supported Providers
- **Google Gemini** (Default): `gemini-2.5-flash`, `gemini-1.5-pro`, etc.
- **OpenAI**: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, etc.
- **Anthropic**: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`
- **100+ Other Models**: Via LiteLLM including Llama, PaLM, Cohere, and more

**For complete model names and provider setup**: See [LiteLLM Providers Documentation](https://docs.litellm.ai/docs/providers)

### Usage Examples

```python
# Gemini (Default - Free tier available)
scraper = UniversalScraper(api_key="your_gemini_key")
# Auto-detects as gemini-2.5-flash

# OpenAI
scraper = UniversalScraper(api_key="sk-...", model_name="gpt-4")

# Anthropic Claude
scraper = UniversalScraper(api_key="sk-ant-...", model_name="claude-3-haiku-20240307")

# Environment variable approach
# Set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY
scraper = UniversalScraper()  # Auto-detects from env vars

# Any other provider from LiteLLM (see link above for model names)
scraper = UniversalScraper(api_key="your_api_key", model_name="llama-2-70b-chat")
```

### Model Configuration Guide

**Quick Reference for Popular Models:**
```python
# Gemini Models
model_name="gemini-2.5-flash"        # Fast, efficient
model_name="gemini-1.5-pro"          # More capable

# OpenAI Models  
model_name="gpt-4"                   # Most capable
model_name="gpt-4o-mini"             # Fast, cost-effective
model_name="gpt-3.5-turbo"           # Legacy but reliable

# Anthropic Models
model_name="claude-3-opus-20240229"      # Most capable
model_name="claude-3-sonnet-20240229"    # Balanced
model_name="claude-3-haiku-20240307"     # Fast, efficient

# Other Popular Models (see LiteLLM docs for setup)
model_name="llama-2-70b-chat"        # Meta Llama
model_name="command-nightly"          # Cohere
model_name="palm-2-chat-bison"        # Google PaLM
```

**🔗 Complete Model List**: Visit [LiteLLM Providers Documentation](https://docs.litellm.ai/docs/providers) for:
- All available model names
- Provider-specific API key setup
- Environment variable configuration
- Rate limits and pricing information

### Model Auto-Detection
If you don't specify a model, the scraper automatically selects:
- **Gemini**: If `GEMINI_API_KEY` is set or API key contains "AIza"
- **OpenAI**: If `OPENAI_API_KEY` is set or API key starts with "sk-"
- **Anthropic**: If `ANTHROPIC_API_KEY` is set or API key starts with "sk-ant-"

## Troubleshooting

### Common Issues

1. **API Key Error**: Make sure your API key is valid and set correctly:
   - Gemini: Set `GEMINI_API_KEY` or pass directly
   - OpenAI: Set `OPENAI_API_KEY` or pass directly
   - Anthropic: Set `ANTHROPIC_API_KEY` or pass directly
2. **Model Not Found**: Ensure you're using the correct model name for your provider
3. **Empty Results**: The AI might need more specific field names or the page might not contain the expected data
4. **Network Errors**: Some sites block scrapers - the tool uses cloudscraper to handle most cases
5. **Model Name Issues**: Check [LiteLLM Providers](https://docs.litellm.ai/docs/providers) for correct model names and setup instructions

### Debug Mode

Enable debug logging to see what's happening:

```python
import logging
scraper = UniversalScraper(api_key="your_key", log_level=logging.DEBUG)
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and improvements.

## Contributors

[Contributors List](https://github.com/pushpenderindia/universal-scraper/graphs/contributors)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `pytest` to run testcases
5. Test PEP Standard: 

```
flake8 universal_scraper/ --count --select=E9,F63,F7,F82 --show-source --statistics

flake8 universal_scraper/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and release notes.
