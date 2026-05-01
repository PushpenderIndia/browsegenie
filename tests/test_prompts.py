"""Tests for agent/prompts.py: SYSTEM_PROMPT constant and capture_page_state function."""

from unittest.mock import MagicMock

from browsegenie.core.browser_agent.agent.prompts import SYSTEM_PROMPT, capture_page_state
from browsegenie.core.browser_agent.heuristic_resolver import KNOWN_TARGETS


class TestSystemPrompt:
    """Tests for the SYSTEM_PROMPT constant."""

    def test_system_prompt_is_nonempty_string(self):
        """Test that SYSTEM_PROMPT is a non-empty string of reasonable length."""
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 100

    def test_all_known_targets_in_prompt(self):
        """Test that every KNOWN_TARGETS entry is mentioned in SYSTEM_PROMPT."""
        for target in KNOWN_TARGETS:
            assert target in SYSTEM_PROMPT, f"'{target}' missing from SYSTEM_PROMPT"

    def test_prompt_includes_done_instruction(self):
        """Test that SYSTEM_PROMPT instructs the agent to call done() when finished."""
        assert "done" in SYSTEM_PROMPT.lower()

    def test_prompt_includes_plan_instruction(self):
        """Test that SYSTEM_PROMPT instructs the agent to call plan() first."""
        assert "plan" in SYSTEM_PROMPT


class TestCapturePageState:
    """Tests for the capture_page_state() snapshot function."""

    def _make_browser(
        self,
        url="https://example.com",
        title="Example",
        text="visible text",
        elements=None,
    ):
        """Return a fake browser stub wired up for capture_page_state."""
        if elements is None:
            elements = [{"index": 0, "tag": "button", "text": "Submit"}]
        browser = MagicMock()
        browser.page.url = url
        browser.page.title.return_value = title
        body = MagicMock()
        body.inner_text.return_value = text
        browser.page.query_selector.return_value = body
        browser.page.evaluate.return_value = elements
        return browser

    def test_returns_nonempty_string(self):
        """Test that capture_page_state returns a non-empty string."""
        browser = self._make_browser()
        result = capture_page_state(browser)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_url_and_title(self):
        """Test that the snapshot string starts with the URL field and includes the page title."""
        browser = self._make_browser(url="https://test.com", title="Test Page")
        result = capture_page_state(browser)
        assert result.startswith("URL:")
        assert "Title: Test Page" in result

    def test_contains_visible_text(self):
        """Test that the snapshot string includes the visible body text."""
        browser = self._make_browser(text="hello world content")
        result = capture_page_state(browser)
        assert "hello world content" in result

    def test_text_capped_at_1500_chars(self):
        """Test that body text in the snapshot is truncated to at most 1500 characters."""
        browser = self._make_browser(text="z" * 3000)
        result = capture_page_state(browser)
        assert "z" * 1501 not in result

    def test_exception_falls_back_to_current_url(self):
        """Test that an exception during snapshot capture falls back to the URL-only format."""
        browser = MagicMock()
        browser.page.url = "bad-page"
        browser.page.title.side_effect = Exception("boom")
        browser.current_url.return_value = "https://fallback.com"
        result = capture_page_state(browser)
        assert "State unavailable" in result
        assert result.startswith("URL:")

    def test_contains_elements_block(self):
        """Test that the snapshot contains an Elements section."""
        browser = self._make_browser(
            elements=[{"index": 0, "tag": "input", "text": "Search"}]
        )
        result = capture_page_state(browser)
        assert "Elements" in result
