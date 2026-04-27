"""Tests for TechStackDetector."""

from browsegenie.core.tech_stack_detector import TechStackDetector


class TestTechStackDetector:
    """Test cases for the TechStackDetector class."""

    def setup_method(self):
        """Set up a fresh TechStackDetector for each test."""
        self.detector = TechStackDetector()

    # ── detect() — static pages ──────────────────────────────────────────────

    def test_static_page_returns_not_spa(self):
        """Test that a page with substantial visible text is classified as static."""
        long_text = "This is a static page with lots of real visible text content. " * 5
        html = f"<html><body><p>{long_text}</p></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is False
        assert result["framework"] is None
        assert result["reason"] == "Static page"

    # ── Framework markers ────────────────────────────────────────────────────

    def test_detects_nextjs_by_data(self):
        """Test detection of Next.js via the __NEXT_DATA__ script tag."""
        html = '<html><body><script id="__NEXT_DATA__" type="application/json">{}</script></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Next.js"

    def test_detects_nuxt(self):
        """Test detection of Nuxt.js via the __NUXT__ window variable."""
        html = "<html><body><script>window.__NUXT__={}</script></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Nuxt.js"

    def test_detects_gatsby(self):
        """Test detection of Gatsby via the ___gatsby root element id."""
        html = "<html><body><div id='___gatsby'></div></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Gatsby"

    def test_detects_remix(self):
        """Test detection of Remix via the __remixContext window variable."""
        html = "<html><body><script>window.__remixContext={}</script></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Remix"

    def test_detects_sveltekit(self):
        """Test detection of SvelteKit via the __sveltekit_data window variable."""
        html = "<html><body><script>window.__sveltekit_data={}</script></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "SvelteKit"

    def test_detects_astro(self):
        """Test detection of Astro via the astro-island custom element."""
        html = "<html><body><astro-island></astro-island></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Astro"

    def test_detects_angular_ng_version(self):
        """Test detection of Angular via the ng-version attribute."""
        html = '<html ng-version="14.0.0"><body><app-root></app-root></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Angular"

    def test_detects_react_data_reactroot(self):
        """Test detection of React via the data-reactroot attribute."""
        html = '<html><body><div data-reactroot="">content</div></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "React"

    def test_detects_react_by_root_id_double_quotes(self):
        """Test detection of React via id="root" with double quotes."""
        html = '<html><body><div id="root"></div></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "React"

    def test_detects_react_by_root_id_single_quotes(self):
        """Test detection of React via id='root' with single quotes."""
        html = "<html><body><div id='root'></div></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "React"

    def test_detects_vue_by_app_id(self):
        """Test detection of Vue via the id="app" mount point."""
        html = '<html><body><div id="app"></div></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Vue"

    # ── Script pattern detection ─────────────────────────────────────────────

    def test_detects_nextjs_by_script_path(self):
        """Test detection of Next.js via /_next/static/ script path."""
        html = '<html><body><script src="/_next/static/chunks/main.js"></script><p>x</p></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Next.js"

    def test_detects_cra_main_bundle(self):
        """Test detection of Create React App via the /static/js/main. bundle pattern."""
        html = '<html><body><script src="/static/js/main.abc123.js"></script></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "React (CRA)"

    def test_detects_nuxt_script(self):
        """Test detection of Nuxt.js via the /_nuxt/ script path."""
        html = '<html><body><script src="/_nuxt/app.js"></script></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Nuxt.js"

    def test_detects_angular_runtime(self):
        """Test detection of Angular via the runtime.js bundle script."""
        html = '<html><body><script src="/runtime.js"></script></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Angular"

    def test_detects_hashed_bundle(self):
        """Test detection of unknown SPA via a generic hashed JS bundle filename."""
        html = '<html><body><script src="/main.a1b2c3d4.js"></script></body></html>'
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Unknown SPA"

    # ── Empty body detection ─────────────────────────────────────────────────

    def test_empty_body_detected_as_spa(self):
        """Test that a body with no visible text is classified as an unknown SPA."""
        html = "<html><body><div></div></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is True
        assert result["framework"] == "Unknown SPA"

    def test_no_body_tag(self):
        """Test that HTML without a body tag is not misclassified as an SPA."""
        html = "<html><div>no body tag here</div></html>"
        result = self.detector.detect(html * 5)
        assert result["is_spa"] is False

    def test_short_body_text(self):
        """Test that a body with fewer than MIN_BODY_TEXT_LENGTH chars is classified as SPA."""
        html = "<html><body>short</body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is True

    def test_long_body_text_is_static(self):
        """Test that a body with substantial text content is correctly classified as static."""
        long_text = "A" * 300
        html = f"<html><body><p>{long_text}</p></body></html>"
        result = self.detector.detect(html)
        assert result["is_spa"] is False

    # ── Return structure ─────────────────────────────────────────────────────

    def test_result_has_required_keys(self):
        """Test that detect() always returns a dict with is_spa, framework, and reason keys."""
        result = self.detector.detect("<html><body>content</body></html>")
        assert "is_spa" in result
        assert "framework" in result
        assert "reason" in result
