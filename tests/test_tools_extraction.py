"""Tests for browser-agent extraction tools: get_page_content, find_elements, get_interactive_elements, execute_js."""

from unittest.mock import MagicMock

from browsegenie.core.browser_agent.tools.extraction import (
    execute_js,
    find_elements,
    get_interactive_elements,
    get_page_content,
)


def _page(url="https://example.com", title="Example", text="Some body text"):
    """Return a mock Playwright Page configured for extraction tests."""
    page = MagicMock()
    page.url = url
    page.title.return_value = title
    body = MagicMock()
    body.inner_text.return_value = text
    page.query_selector.return_value = body
    return page


class TestGetPageContent:
    """Tests for the get_page_content() extraction tool."""

    def test_returns_url_title_text(self):
        """Test that get_page_content returns url, title, and text keys."""
        page = _page()
        result = get_page_content(page)
        assert result["url"] == "https://example.com"
        assert result["title"] == "Example"
        assert "Some body text" in result["text"]

    def test_text_truncated_to_3000_chars(self):
        """Test that visible text is capped at 3000 characters."""
        long_text = "x" * 5000
        page = _page(text=long_text)
        result = get_page_content(page)
        assert len(result["text"]) <= 3000

    def test_body_none_returns_empty_text(self):
        """Test that get_page_content returns an empty text string when body element is None."""
        page = _page()
        page.query_selector.return_value = None
        result = get_page_content(page)
        assert result["text"] == ""

    def test_inner_text_exception_returns_empty_text(self):
        """Test that get_page_content returns empty text when inner_text raises an exception."""
        page = _page()
        page.query_selector.return_value.inner_text.side_effect = Exception("DOM error")
        result = get_page_content(page)
        assert result["text"] == ""


class TestFindElements:
    """Tests for the find_elements() extraction tool."""

    def test_returns_selector_total_and_results(self):
        """Test that find_elements returns selector, total, and results from page.evaluate."""
        page = MagicMock()
        page.evaluate.return_value = {
            "total": 2,
            "results": [{"tag": "a"}, {"tag": "a"}],
        }
        result = find_elements(page, "a")
        assert result["selector"] == "a"
        assert result["total"] == 2
        assert len(result["results"]) == 2

    def test_exception_returns_error_dict(self):
        """Test that find_elements returns an error dict when page.evaluate raises."""
        page = MagicMock()
        page.evaluate.side_effect = Exception("JS error")
        result = find_elements(page, ".bad-selector")
        assert "error" in result
        assert result["selector"] == ".bad-selector"

    def test_limit_forwarded_to_evaluate(self):
        """Test that the limit parameter is included in the arguments passed to evaluate."""
        page = MagicMock()
        page.evaluate.return_value = {"total": 0, "results": []}
        find_elements(page, "div", limit=5)
        call_args = page.evaluate.call_args
        assert 5 in call_args[0][1].values()


class TestGetInteractiveElements:
    """Tests for the get_interactive_elements() extraction tool."""

    def test_returns_elements_and_count(self):
        """Test that get_interactive_elements returns an elements list and the correct count."""
        page = MagicMock()
        page.evaluate.return_value = [
            {"index": 0, "tag": "button"},
            {"index": 1, "tag": "input"},
        ]
        result = get_interactive_elements(page)
        assert result["count"] == 2
        assert len(result["elements"]) == 2

    def test_empty_page_returns_zero_count(self):
        """Test that an empty elements list yields count=0."""
        page = MagicMock()
        page.evaluate.return_value = []
        result = get_interactive_elements(page)
        assert result["count"] == 0
        assert result["elements"] == []


class TestExecuteJs:
    """Tests for the execute_js() extraction tool."""

    def test_happy_path_returns_result(self):
        """Test that execute_js returns a result dict with the stringified evaluate value."""
        page = MagicMock()
        page.evaluate.return_value = 42
        result = execute_js(page, "1 + 41")
        assert result["result"] == "42"

    def test_exception_returns_error_dict(self):
        """Test that execute_js returns an error dict when page.evaluate raises."""
        page = MagicMock()
        page.evaluate.side_effect = Exception("syntax error")
        result = execute_js(page, "~~~")
        assert "error" in result
        assert "syntax error" in result["error"]

    def test_result_truncated_to_5000(self):
        """Test that the stringified result is capped at 5000 characters."""
        page = MagicMock()
        page.evaluate.return_value = "y" * 10000
        result = execute_js(page, "bigString()")
        assert len(result["result"]) <= 5000
