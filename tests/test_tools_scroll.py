"""Tests for browser-agent scroll tools: scroll, scroll_to_element, scroll_to_bottom, scroll_to_top."""

from unittest.mock import MagicMock

from browsegenie.core.browser_agent.tools.scroll import (
    scroll,
    scroll_to_bottom,
    scroll_to_element,
    scroll_to_top,
)


def _page():
    """Return a mock Playwright Page."""
    return MagicMock()


class TestScroll:
    """Tests for the scroll() tool."""

    def test_scroll_down(self):
        """Test that scroll('down') evaluates the correct scrollBy JS expression."""
        page = _page()
        result = scroll(page, direction="down", pixels=300)
        page.evaluate.assert_called_once_with("window.scrollBy(0, 300)")
        assert result["scrolled"] == "down"
        assert result["pixels"] == 300

    def test_scroll_up(self):
        """Test that scroll('up') evaluates a negative vertical scrollBy."""
        page = _page()
        result = scroll(page, direction="up", pixels=200)
        page.evaluate.assert_called_once_with("window.scrollBy(0, -200)")
        assert result["scrolled"] == "up"

    def test_scroll_right(self):
        """Test that scroll('right') evaluates a horizontal-positive scrollBy."""
        page = _page()
        result = scroll(page, direction="right", pixels=100)
        page.evaluate.assert_called_once_with("window.scrollBy(100, 0)")
        assert result["scrolled"] == "right"

    def test_scroll_left(self):
        """Test that scroll('left') evaluates a horizontal-negative scrollBy."""
        page = _page()
        result = scroll(page, direction="left", pixels=100)
        page.evaluate.assert_called_once_with("window.scrollBy(-100, 0)")
        assert result["scrolled"] == "left"

    def test_invalid_direction_returns_error(self):
        """Test that an unrecognised direction returns an error dict without calling evaluate."""
        page = _page()
        result = scroll(page, direction="diagonal")
        assert "error" in result
        assert "diagonal" in result["error"]
        page.evaluate.assert_not_called()

    def test_default_pixels_is_500(self):
        """Test that the default pixel amount is 500 when not specified."""
        page = _page()
        result = scroll(page)
        assert result["pixels"] == 500


class TestScrollToElement:
    """Tests for the scroll_to_element() tool."""

    def test_element_found(self):
        """Test that scroll_to_element calls scroll_into_view_if_needed when element is found."""
        page = _page()
        el = MagicMock()
        page.query_selector.return_value = el
        result = scroll_to_element(page, "#target")
        el.scroll_into_view_if_needed.assert_called_once()
        assert result["found"] is True
        assert result["selector"] == "#target"

    def test_element_not_found(self):
        """Test that scroll_to_element returns found=False when the selector matches nothing."""
        page = _page()
        page.query_selector.return_value = None
        result = scroll_to_element(page, "#missing")
        assert result["found"] is False
        assert result["selector"] == "#missing"


class TestScrollToBottom:
    """Tests for the scroll_to_bottom() tool."""

    def test_scroll_to_bottom_evaluates_js(self):
        """Test that scroll_to_bottom calls page.evaluate with the scrollHeight expression."""
        page = _page()
        result = scroll_to_bottom(page)
        page.evaluate.assert_called_once_with(
            "window.scrollTo(0, document.body.scrollHeight)"
        )
        assert result["action"] == "scroll_to_bottom"


class TestScrollToTop:
    """Tests for the scroll_to_top() tool."""

    def test_scroll_to_top_evaluates_js(self):
        """Test that scroll_to_top calls page.evaluate with the scrollTo(0,0) expression."""
        page = _page()
        result = scroll_to_top(page)
        page.evaluate.assert_called_once_with("window.scrollTo(0, 0)")
        assert result["action"] == "scroll_to_top"
