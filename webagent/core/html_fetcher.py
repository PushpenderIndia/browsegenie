import cloudscraper
import time
import logging
import os
from datetime import datetime
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from .tech_stack_detector import TechStackDetector


class HtmlFetcher:
    def __init__(self, temp_dir="temp"):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = temp_dir
        self.raw_html_dir = os.path.join(temp_dir, "raw_html")
        os.makedirs(self.raw_html_dir, exist_ok=True)
        self.detector = TechStackDetector()

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def fetch_with_cloudscraper(self, url):
        """
        Fetch HTML content using cloudscraper with custom headers
        """
        try:
            scraper = cloudscraper.create_scraper()
            scraper.headers.update(self.headers)

            self.logger.info(f"Fetching {url} with cloudscraper...")
            response = scraper.get(url, timeout=30)
            response.raise_for_status()

            self.logger.info(
                f"Successfully fetched content with cloudscraper. "
                f"Length: {len(response.text)}"
            )
            return response.text

        except Exception as e:
            self.logger.error(f"Cloudscraper failed for {url}: {str(e)}")
            return None

    def fetch_with_selenium(self, url, wait_time=10):
        """
        Fetch HTML content using selenium with headless Chrome
        """
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(
                f'--user-agent={self.headers["User-Agent"]}'
            )
            chrome_options.add_argument(
                "--disable-blink-features=AutomationControlled"
            )
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option(
                "useAutomationExtension", False
            )

            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', "
                "{get: () => undefined})"
            )

            self.logger.info(f"Fetching {url} with selenium...")
            driver.get(url)

            # Wait for page to load
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional wait for dynamic content
            time.sleep(3)

            html_content = driver.page_source
            self.logger.info(
                f"Successfully fetched content with selenium. "
                f"Length: {len(html_content)}"
            )

            return html_content

        except TimeoutException:
            self.logger.error(f"Selenium timeout for {url}")
            return None
        except WebDriverException as e:
            self.logger.error(f"Selenium WebDriver error for {url}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Selenium failed for {url}: {str(e)}")
            return None
        finally:
            if driver:
                driver.quit()

    def _save_raw_html(self, url, html_content, method):
        """Save raw HTML to temp folder for debugging"""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "").replace(".", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{domain}_{timestamp}_{method}.html"
            filepath = os.path.join(self.raw_html_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            self.logger.debug(f"Raw HTML saved to: {filepath}")
            return filepath
        except Exception as e:
            self.logger.warning(f"Failed to save raw HTML: {e}")
            return None

    def fetch_html(self, url, save_temp=True):
        """
        Fetch HTML for a URL, choosing the right strategy automatically.

        - Static pages: CloudScraper (fast, no browser overhead)
        - SPAs (React/Vue/Angular/Next.js/…): skip directly to Selenium so
          JavaScript has a chance to render the actual content.
        - CloudScraper failures: fall back to Selenium regardless.
        """
        self.logger.info(f"Starting to fetch HTML for: {url}")

        # Step 1: Fetch with cloudscraper to get the raw HTML shell
        html = self.fetch_with_cloudscraper(url)

        if html and len(html) > 100:
            # Step 2: Detect whether the page needs JS rendering
            detection = self.detector.detect(html)
            if detection["is_spa"]:
                self.logger.info(
                    f"SPA detected ({detection['framework']}): "
                    f"{detection['reason']} — switching to selenium"
                )
            else:
                self.logger.info("Successfully fetched HTML with cloudscraper")
                if save_temp:
                    self._save_raw_html(url, html, "cloudscraper")
                return html
        else:
            self.logger.info(
                "Cloudscraper failed or returned insufficient content, "
                "trying selenium..."
            )

        # Step 3: Use Selenium (SPA or cloudscraper failure)
        html = self.fetch_with_selenium(url)
        if html and len(html) > 100:
            self.logger.info("Successfully fetched HTML with selenium")
            if save_temp:
                self._save_raw_html(url, html, "selenium")
            return html

        # Both methods failed
        self.logger.error(f"Both methods failed to fetch HTML for {url}")
        raise Exception(
            f"Failed to fetch HTML content for {url} using both "
            f"cloudscraper and selenium"
        )
