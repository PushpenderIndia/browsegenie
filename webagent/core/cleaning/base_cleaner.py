"""
Base cleaner with common utilities and configuration
"""
import logging
import os
from datetime import datetime
from urllib.parse import urlparse


class BaseHtmlCleaner:
    """Base class for HTML cleaning components"""

    def __init__(self, temp_dir="temp"):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = temp_dir
        self.cleaned_html_dir = os.path.join(temp_dir, "cleaned_html")
        os.makedirs(self.cleaned_html_dir, exist_ok=True)

        # Common tag definitions used across cleaners
        self.header_tags = ["header", "nav", "aside"]
        self.footer_tags = ["footer"]
        self.noise_tags = ["script", "style", "meta", "link", "noscript"]

        # Non-essential attributes that can be safely removed
        self.remove_attributes = [
            # Styling and presentation
            "style",
            # JavaScript event handlers
            "onclick", "onload", "onerror", "onmouseover", "onmouseout",
            "onmousedown", "onmouseup", "onfocus", "onblur", "onchange",
            "onsubmit", "onreset", "onkeydown", "onkeyup", "onkeypress",
            "ondblclick", "oncontextmenu", "onwheel", "ondrag", "ondrop",
            "ondragover", "ondragenter", "ondragleave", "ondragstart",
            "ondragend", "onscroll", "onresize", "onselect",
            # Analytics and tracking
            "data-analytics", "data-tracking", "data-ga", "data-gtm",
            "data-fb", "data-pixel", "data-track", "data-event",
            "data-label", "data-category", "data-action", "data-google-analytics",
            "data-mixpanel", "data-segment", "data-amplitude",
            # Testing and debugging
            "data-testid", "data-test", "data-cy", "data-selenium",
            "data-qa", "data-automation", "data-e2e", "data-test-id",
            "data-jest", "data-playwright",
            # Accessibility (only non-essential ones)
            "aria-describedby", "aria-labelledby", "aria-controls",
            "aria-owns", "aria-flowto", "aria-activedescendant", "aria-details",
            # Interaction and usability (non-essential)
            "tabindex", "accesskey", "draggable", "spellcheck", "contenteditable",
            "autocomplete", "autocapitalize", "autocorrect",
            # Layout and positioning (CSS-related)
            "align", "valign", "bgcolor", "background", "border",
            "cellpadding", "cellspacing", "width", "height", "size",
            "color", "face", "clear",
            # Meta information (SEO/social)
            "data-description", "data-keywords", "data-author", "data-copyright",
            "data-og-", "data-twitter-", "data-fb-", "data-linkedin-",
            # Framework/library specific (non-essential)
            "data-react", "data-vue", "data-angular", "data-ember",
            "data-backbone", "ng-", "v-", "x-data", "x-show", "x-if", "alpine-",
            # Performance and loading
            "loading", "decoding", "fetchpriority", "referrerpolicy",
            # Form validation styling
            "data-valid", "data-invalid", "data-error", "data-success",
            # Animation and transition
            "data-animate", "data-animation", "data-transition",
            "data-duration", "data-delay", "data-ease",
            # Theme and appearance
            "data-theme", "data-mode", "data-variant", "data-color-scheme",
            # Tooltip and popover positioning
            "data-placement", "data-offset", "data-boundary", "data-flip",
            # Security (non-essential)
            "crossorigin", "integrity", "nonce",
        ]

        # Essential attributes that should NEVER be removed
        self.essential_attributes = {
            # Core content attributes and selectors
            "id", "class", "name", "value", "content", "text", "innerHTML", "innerText",
            # Links and navigation
            "href", "src", "action", "target", "download",
            # Form data
            "type", "placeholder", "required", "disabled", "readonly",
            "checked", "selected", "multiple", "accept", "pattern",
            "min", "max", "step", "minlength", "maxlength",
            # Essential meta information
            "title", "alt", "lang", "charset", "encoding",
            # Data attributes that might contain extractable data
            "data-price", "data-value", "data-id", "data-name", "data-title",
            "data-url", "data-date", "data-time", "data-location", "data-phone",
            "data-email", "data-rating", "data-review", "data-count",
            "data-quantity", "data-amount", "data-currency", "data-status",
            "data-category", "data-type", "data-brand", "data-model",
            "data-sku", "data-description", "data-summary",
            # Essential accessibility
            "aria-label", "aria-hidden", "aria-expanded", "aria-selected",
            "aria-checked", "aria-pressed", "aria-current", "aria-live",
            "aria-atomic", "role",
            # Media attributes
            "controls", "autoplay", "loop", "muted", "poster", "preload",
            # Table structure
            "colspan", "rowspan", "headers", "scope",
            # List structure
            "start", "reversed",
            # Essential form attributes
            "for", "form", "method", "enctype", "novalidate",
            # Common selector attributes
            "rel", "property", "itemprop", "itemtype", "itemscope",
            # Custom data attributes for content identification
            "data-role", "data-component", "data-module", "data-section",
            "data-element", "data-widget", "data-container",
        }

    def save_temp_html(self, url, html_content, stage):
        """Save cleaned HTML at different stages for debugging"""
        try:
            if url:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace("www.", "").replace(".", "_")
            else:
                domain = "unknown"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{domain}_{timestamp}_{stage}.html"
            filepath = os.path.join(self.cleaned_html_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            self.logger.debug(f"Cleaned HTML ({stage}) saved to: {filepath}")
            return filepath
        except Exception as e:
            self.logger.warning(f"Failed to save cleaned HTML: {e}")
            return None
