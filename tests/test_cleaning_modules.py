"""Tests for cleaning sub-modules: UrlReplacer, AttributeCleaner, DuplicateFinder."""

import tempfile

from bs4 import BeautifulSoup

from browsegenie.core.cleaning.attribute_cleaner import AttributeCleaner
from browsegenie.core.cleaning.duplicate_finder import DuplicateFinder
from browsegenie.core.cleaning.url_replacer import UrlReplacer


def _soup(html: str) -> BeautifulSoup:
    """Parse an HTML string and return a BeautifulSoup object."""
    return BeautifulSoup(html, "html.parser")


def _cleaner(cls):
    """Instantiate a cleaner class with an isolated temp directory."""
    return cls(temp_dir=tempfile.mkdtemp())


# ── UrlReplacer ───────────────────────────────────────────────────────────────

class TestUrlReplacer:
    """Test cases for the UrlReplacer cleaning stage."""

    def setup_method(self):
        """Set up a fresh UrlReplacer with an isolated temp directory."""
        self.replacer = _cleaner(UrlReplacer)

    def test_img_src_replaced(self):
        """Test that a long img src URL is replaced with [IMG_URL]."""
        soup = _soup('<img src="https://example.com/very/long/path/image.jpg" alt="x">')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("img")["src"] == "[IMG_URL]"

    def test_anchor_href_replaced(self):
        """Test that a long anchor href is replaced with [LINK_URL]."""
        soup = _soup('<a href="https://example.com/very/long/path/to/page.html">Link</a>')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("a")["href"] == "[LINK_URL]"

    def test_form_action_replaced(self):
        """Test that a long form action URL is replaced with [FORM_URL]."""
        soup = _soup('<form action="https://example.com/submit/the/form/endpoint">x</form>')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("form")["action"] == "[FORM_URL]"

    def test_script_src_replaced(self):
        """Test that a script src URL is replaced with [RESOURCE_URL]."""
        soup = _soup('<script src="https://example.com/static/js/bundle.min.js"></script>')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("script")["src"] == "[RESOURCE_URL]"

    def test_iframe_src_replaced(self):
        """Test that an iframe src URL is replaced with [IFRAME_URL]."""
        soup = _soup('<iframe src="https://example.com/embeds/video/player"></iframe>')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("iframe")["src"] == "[IFRAME_URL]"

    def test_short_url_not_replaced(self):
        """Test that short relative URLs (<=20 chars) are left untouched."""
        soup = _soup('<a href="/page">Link</a>')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("a")["href"] == "/page"

    def test_already_placeholder_not_replaced(self):
        """Test that an attribute already containing a [URL placeholder is not double-replaced."""
        soup = _soup('<img src="[IMG_URL]">')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("img")["src"] == "[IMG_URL]"

    def test_data_src_replaced(self):
        """Test that lazy-load data-src attributes on images are replaced with [IMG_URL]."""
        soup = _soup('<img data-src="https://cdn.example.com/images/product/photo.jpg">')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("img")["data-src"] == "[IMG_URL]"

    def test_link_href_replaced(self):
        """Test that a <link> element's href is replaced with [RESOURCE_URL]."""
        soup = _soup('<link href="https://cdn.example.com/stylesheets/main.css" rel="stylesheet">')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("link")["href"] == "[RESOURCE_URL]"

    def test_returns_soup(self):
        """Test that the method returns the same BeautifulSoup object it received."""
        soup = _soup('<div>no urls here</div>')
        result = self.replacer.replace_url_sources_with_placeholders(soup)
        assert result is soup

    def test_generic_div_data_href_replaced(self):
        """Test that a data-href on a non-anchor element is replaced with [HREF_URL]."""
        soup = _soup('<div data-href="https://example.com/some/very/long/path/here">x</div>')
        self.replacer.replace_url_sources_with_placeholders(soup)
        assert soup.find("div")["data-href"] == "[HREF_URL]"


# ── AttributeCleaner ──────────────────────────────────────────────────────────

class TestAttributeCleaner:
    """Test cases for the AttributeCleaner cleaning stage."""

    def setup_method(self):
        """Set up a fresh AttributeCleaner with an isolated temp directory."""
        self.cleaner = _cleaner(AttributeCleaner)

    def test_style_attribute_removed(self):
        """Test that inline style attributes are removed as non-essential."""
        soup = _soup('<div style="color:red;font-size:12px">content</div>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert "style" not in soup.find("div").attrs

    def test_onclick_removed(self):
        """Test that JavaScript event handlers like onclick are removed."""
        soup = _soup('<button onclick="doSomething()">Click</button>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert "onclick" not in soup.find("button").attrs

    def test_data_testid_removed(self):
        """Test that test/automation attributes like data-testid are removed."""
        soup = _soup('<div data-testid="submit-btn">x</div>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert "data-testid" not in soup.find("div").attrs

    def test_essential_class_kept(self):
        """Test that the class attribute is preserved as an essential selector attribute."""
        soup = _soup('<div class="product-card">content</div>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert soup.find("div")["class"] == ["product-card"]

    def test_essential_id_kept(self):
        """Test that the id attribute is preserved as an essential selector attribute."""
        soup = _soup('<div id="main-content">content</div>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert soup.find("div")["id"] == "main-content"

    def test_data_price_kept(self):
        """Test that data-price is preserved as a useful content attribute."""
        soup = _soup('<div data-price="29.99">$29.99</div>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert soup.find("div").get("data-price") == "29.99"

    def test_data_analytics_removed(self):
        """Test that tracking attributes like data-analytics are removed."""
        soup = _soup('<div data-analytics="purchase">item</div>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert "data-analytics" not in soup.find("div").attrs

    def test_href_kept(self):
        """Test that href is preserved as an essential navigation attribute."""
        soup = _soup('<a href="/products">Products</a>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert soup.find("a")["href"] == "/products"

    def test_multiple_elements_processed(self):
        """Test that non-essential attributes are removed across multiple nested elements."""
        soup = _soup('''
            <div style="margin:0" class="card">
                <a onclick="track()" href="/page">Link</a>
            </div>
        ''')
        self.cleaner.remove_non_essential_attributes(soup)
        assert "style" not in soup.find("div").attrs
        assert "onclick" not in soup.find("a").attrs
        assert soup.find("div")["class"] == ["card"]
        assert soup.find("a")["href"] == "/page"

    def test_returns_soup(self):
        """Test that the method returns the same BeautifulSoup object it received."""
        soup = _soup('<div>content</div>')
        result = self.cleaner.remove_non_essential_attributes(soup)
        assert result is soup

    def test_data_rating_kept(self):
        """Test that data-rating is preserved as a useful content attribute."""
        soup = _soup('<div data-rating="4.5">★★★★½</div>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert soup.find("div").get("data-rating") == "4.5"

    def test_ng_prefix_removed(self):
        """Test that Angular ng-* directive attributes are removed as non-essential."""
        soup = _soup('<div ng-repeat="item in items">content</div>')
        self.cleaner.remove_non_essential_attributes(soup)
        assert "ng-repeat" not in soup.find("div").attrs


# ── DuplicateFinder ───────────────────────────────────────────────────────────

class TestDuplicateFinder:
    """Test cases for the DuplicateFinder cleaning stage."""

    def setup_method(self):
        """Set up a fresh DuplicateFinder with an isolated temp directory."""
        self.finder = _cleaner(DuplicateFinder)

    def test_get_element_signature_basic(self):
        """Test that get_element_signature returns a non-empty string containing the tag and class."""
        soup = _soup('<div class="card" role="article"></div>')
        elem = soup.find("div")
        sig = self.finder.get_element_signature(elem)
        assert sig is not None
        assert "div" in sig
        assert "card" in sig

    def test_get_element_signature_no_name(self):
        """Test that a text node (no tag name) returns None from get_element_signature."""
        soup = _soup("plain text")
        text_node = soup.contents[0]
        assert self.finder.get_element_signature(text_node) is None

    def test_get_element_signature_sorted_classes(self):
        """Test that class names in the signature are sorted for consistent hashing."""
        soup = _soup('<div class="z-class a-class m-class"></div>')
        elem = soup.find("div")
        sig = self.finder.get_element_signature(elem)
        assert sig is not None
        assert sig.index("a-class") < sig.index("z-class")

    def test_get_element_signature_with_data_attr(self):
        """Test that data-* attributes are included in the element signature."""
        soup = _soup('<div data-type="product" data-id="1"></div>')
        elem = soup.find("div")
        sig = self.finder.get_element_signature(elem)
        assert sig is not None
        assert "data-type" in sig

    def test_get_element_signature_with_children(self):
        """Test that child element structure is captured in the signature."""
        soup = _soup('<ul><li>one</li><li>two</li><span>text</span></ul>')
        elem = soup.find("ul")
        sig = self.finder.get_element_signature(elem)
        assert sig is not None
        assert "children:" in sig

    def test_get_structural_hash_returns_string(self):
        """Test that get_structural_hash returns a non-empty string for a valid element."""
        soup = _soup('<div class="card"><h2>Title</h2><p>Body</p></div>')
        elem = soup.find("div")
        h = self.finder.get_structural_hash(elem)
        assert isinstance(h, str)
        assert len(h) > 0

    def test_same_structure_same_hash(self):
        """Test that two structurally identical elements produce the same hash."""
        html = '<div class="card"><h2>Title</h2><p>Body</p></div>'
        e1 = _soup(html).find("div")
        e2 = _soup(html).find("div")
        assert self.finder.get_structural_hash(e1) == self.finder.get_structural_hash(e2)

    def test_different_structure_different_hash(self):
        """Test that structurally distinct elements produce different hashes."""
        e1 = _soup('<div class="card"><h2>Title</h2></div>').find("div")
        e2 = _soup('<div class="item"><p>Body</p></div>').find("div")
        assert self.finder.get_structural_hash(e1) != self.finder.get_structural_hash(e2)

    def test_find_repeating_structures_no_body(self):
        """Test that find_repeating_structures returns an empty list when there is no body tag."""
        soup = _soup('<div>no body</div>')
        result = self.finder.find_repeating_structures(soup)
        assert result == []

    def test_remove_repeating_structures_returns_soup(self):
        """Test that remove_repeating_structures returns the modified soup object."""
        cards = ""
        for i in range(5):
            cards += f'<div class="card" data-id="{i}"><h2>Product {i}</h2><p>Price: ${i * 10}.00 — great deal, buy now before stock runs out!</p><a href="/p/{i}">View</a></div>'
        soup = _soup(f"<html><body>{cards}</body></html>")
        result = self.finder.remove_repeating_structures(soup, min_keep=2, min_total=3)
        assert result is soup

    def test_find_repeating_structures_identical_cards(self):
        """Test that find_repeating_structures returns a list (possibly empty) for identical card elements."""
        cards = ""
        for i in range(5):
            cards += f'<div class="card" data-id="{i}"><h2>Product {i}</h2><p>Price: ${i * 10}.00 — great deal, buy now before stock runs out!</p><a href="/p/{i}">View</a></div>'
        soup = _soup(f"<html><body>{cards}</body></html>")
        to_remove = self.finder.find_repeating_structures(soup, min_keep=2, min_total=3)
        assert isinstance(to_remove, list)
