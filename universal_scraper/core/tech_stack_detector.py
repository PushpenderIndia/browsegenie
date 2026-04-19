import re
import logging


class TechStackDetector:
    """
    Detects whether a page is a Single Page Application (SPA) or a
    statically-rendered page by inspecting its HTML content.

    SPAs (React, Vue, Angular, Next.js, etc.) serve a minimal HTML shell and
    rely on JavaScript to render content, so they require Selenium for
    meaningful extraction. Static pages can be handled by CloudScraper alone.
    """

    # HTML markers that indicate a JS-rendered SPA
    SPA_MARKERS = [
        # React
        'id="root"',
        "id='root'",
        "data-reactroot",
        # Vue
        'id="app"',
        "id='app'",
        # Angular
        "ng-version",
        "<app-root",
        # Next.js
        "__NEXT_DATA__",
        "__NEXT_LOADED_PAGES__",
        # Nuxt.js
        "__NUXT__",
        "data-n-head",
        # Gatsby
        "gatsby-root",
        "___gatsby",
        # Remix
        "__remixContext",
        # SvelteKit
        "__sveltekit_data",
        # Astro (with client-side hydration)
        "astro-island",
    ]

    # Script src patterns that indicate SPA bundles
    SPA_SCRIPT_PATTERNS = [
        r"/_next/static/",       # Next.js
        r"/static/js/main\.",    # CRA (Create React App)
        r"/static/js/bundle\.",  # CRA
        r"/_nuxt/",              # Nuxt.js
        r"/dist/build\.js",      # Vue CLI
        r"runtime\.js",          # Angular
        r"main\.[a-f0-9]+\.js",  # generic hashed bundles
    ]

    # Minimum visible body text length to consider a page statically rendered
    MIN_BODY_TEXT_LENGTH = 200

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._compiled_script_patterns = [
            re.compile(p) for p in self.SPA_SCRIPT_PATTERNS
        ]

    def detect(self, html: str) -> dict:
        """
        Analyse the HTML and return a detection result.

        Returns:
            {
                "is_spa": bool,
                "framework": str | None,   # e.g. "Next.js", "React", …
                "reason": str              # human-readable explanation
            }
        """
        framework, reason = self._check_markers(html)
        if framework:
            self.logger.info(f"SPA detected: {framework} — {reason}")
            return {"is_spa": True, "framework": framework, "reason": reason}

        framework, reason = self._check_script_patterns(html)
        if framework:
            self.logger.info(f"SPA detected via scripts: {framework} — {reason}")
            return {"is_spa": True, "framework": framework, "reason": reason}

        if self._has_empty_body(html):
            reason = "Body contains almost no visible text (< 200 chars)"
            self.logger.info(f"SPA detected: unknown framework — {reason}")
            return {"is_spa": True, "framework": "Unknown SPA", "reason": reason}

        return {"is_spa": False, "framework": None, "reason": "Static page"}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_markers(self, html: str):
        """Return (framework, reason) if an inline SPA marker is found."""
        marker_framework_map = {
            "__NEXT_DATA__": "Next.js",
            "__NEXT_LOADED_PAGES__": "Next.js",
            "__NUXT__": "Nuxt.js",
            "data-n-head": "Nuxt.js",
            "___gatsby": "Gatsby",
            "gatsby-root": "Gatsby",
            "__remixContext": "Remix",
            "__sveltekit_data": "SvelteKit",
            "astro-island": "Astro",
            "ng-version": "Angular",
            "<app-root": "Angular",
            "data-reactroot": "React",
        }

        for marker, framework in marker_framework_map.items():
            if marker in html:
                return framework, f"Found marker '{marker}'"

        # Generic React/Vue mount points (less specific — check last)
        if 'id="root"' in html or "id='root'" in html:
            return "React", "Found mount point id='root'"
        if 'id="app"' in html or "id='app'" in html:
            return "Vue", "Found mount point id='app'"

        return None, None

    def _check_script_patterns(self, html: str):
        """Return (framework, reason) if a known SPA bundle script is found."""
        script_framework_map = {
            r"/_next/static/": "Next.js",
            r"/static/js/main\.": "React (CRA)",
            r"/static/js/bundle\.": "React (CRA)",
            r"/_nuxt/": "Nuxt.js",
            r"/dist/build\.js": "Vue CLI",
            r"runtime\.js": "Angular",
        }

        for pattern, framework in script_framework_map.items():
            if re.search(pattern, html):
                return framework, f"Found bundle script matching '{pattern}'"

        # Generic hashed bundle (last resort)
        if re.search(r"main\.[a-f0-9]+\.js", html):
            return "Unknown SPA", "Found hashed JS bundle (main.<hash>.js)"

        return None, None

    def _has_empty_body(self, html: str) -> bool:
        """Return True if the <body> contains very little visible text."""
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        if not body_match:
            return False

        body_html = body_match.group(1)
        # Strip all tags to get visible text
        visible_text = re.sub(r"<[^>]+>", "", body_html)
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        return len(visible_text) < self.MIN_BODY_TEXT_LENGTH
