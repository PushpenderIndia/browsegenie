"""Tests for browser-agent interaction tools: click, fill, press_key, hover, select_option, drag_and_drop."""

from unittest.mock import MagicMock

from browsegenie.core.browser_agent.tools.interaction import (
    click,
    drag_and_drop,
    fill,
    hover,
    press_key,
    select_option,
)


def _page():
    """Return a fully wired mock Playwright Page."""
    return MagicMock()


def _handle_with_element(el=None):
    """Return a mock evaluate_handle result whose as_element() returns el."""
    handle = MagicMock()
    handle.as_element.return_value = el
    return handle


class TestClick:
    """Tests for the click() interaction tool."""

    def test_click_by_selector(self):
        """Test that click(selector) uses locator().first to attempt the click."""
        page = _page()
        result = click(page, selector="#submit")
        page.locator.assert_called_once_with("#submit")
        assert result["clicked"] == "#submit"

    def test_click_by_coordinates(self):
        """Test that click(x, y) delegates to page.mouse.click."""
        page = _page()
        result = click(page, x=100, y=200)
        page.mouse.click.assert_called_once_with(100, 200)
        assert "100" in result["clicked"] and "200" in result["clicked"]

    def test_click_by_index_out_of_range(self):
        """Test that click(index) returns an error dict when no element is at that index."""
        page = _page()
        page.evaluate_handle.return_value = _handle_with_element(None)
        result = click(page, index=99)
        assert "error" in result
        assert "99" in result["error"]

    def test_click_by_index_success(self):
        """Test that click(index) scrolls into view and clicks the resolved element."""
        page = _page()
        el = MagicMock()
        page.evaluate_handle.return_value = _handle_with_element(el)
        result = click(page, index=0)
        el.click.assert_called_once()
        assert "element_index=0" in result["clicked"]

    def test_click_no_args_returns_error(self):
        """Test that calling click with no targeting argument returns an error dict."""
        page = _page()
        result = click(page)
        assert "error" in result

    def test_click_selector_locator_failure_uses_js_fallback(self):
        """Test that a locator click failure triggers the JS evaluate fallback."""
        page = _page()
        page.locator.return_value.first.click.side_effect = Exception("not actionable")
        result = click(page, selector="#btn")
        page.evaluate.assert_called()
        assert result["clicked"] == "#btn"

    def test_click_index_scroll_failure_still_clicks(self):
        """Test that a scroll_into_view failure does not prevent the element from being clicked."""
        page = _page()
        el = MagicMock()
        el.scroll_into_view_if_needed.side_effect = Exception("scroll fail")
        page.evaluate_handle.return_value = _handle_with_element(el)
        result = click(page, index=0)
        el.click.assert_called_once()
        assert "element_index=0" in result["clicked"]


class TestFill:
    """Tests for the fill() interaction tool."""

    def test_fill_by_selector(self):
        """Test that fill(selector) calls page.fill to clear and page.type to input text."""
        page = _page()
        result = fill(page, text="hello", selector="#input")
        page.fill.assert_called_once_with("#input", "", timeout=10000)
        page.type.assert_called_once_with("#input", "hello", delay=30)
        assert result["filled"] == "#input"
        assert result["text"] == "hello"

    def test_fill_no_clear(self):
        """Test that fill with clear_first=False skips the initial page.fill clear step."""
        page = _page()
        fill(page, text="world", selector="#input", clear_first=False)
        page.fill.assert_not_called()
        page.type.assert_called_once()

    def test_fill_by_index_success(self):
        """Test that fill(index) resolves the element and types into it."""
        page = _page()
        el = MagicMock()
        page.evaluate_handle.return_value = _handle_with_element(el)
        result = fill(page, text="test", index=1, clear_first=True)
        el.fill.assert_called_once_with("", timeout=10000)
        el.type.assert_called_once_with("test", delay=30)
        assert "element_index=1" in result["filled"]

    def test_fill_by_index_out_of_range(self):
        """Test that fill(index) returns an error dict when the index resolves to None."""
        page = _page()
        page.evaluate_handle.return_value = _handle_with_element(None)
        result = fill(page, text="x", index=50)
        assert "error" in result

    def test_fill_no_args_returns_error(self):
        """Test that fill with neither selector nor index returns an error dict."""
        page = _page()
        result = fill(page, text="orphan")
        assert "error" in result


class TestPressKey:
    """Tests for the press_key() interaction tool."""

    def test_press_key_no_selector(self):
        """Test that press_key without a selector presses the key directly."""
        page = _page()
        result = press_key(page, key="Enter")
        page.focus.assert_not_called()
        page.keyboard.press.assert_called_once_with("Enter")
        assert result["pressed"] == "Enter"

    def test_press_key_with_selector_focuses_first(self):
        """Test that press_key with a selector focuses the element before pressing the key."""
        page = _page()
        press_key(page, key="Tab", selector="#input")
        page.focus.assert_called_once_with("#input", timeout=5000)
        page.keyboard.press.assert_called_once_with("Tab")


class TestHover:
    """Tests for the hover() interaction tool."""

    def test_hover_calls_page_hover(self):
        """Test that hover delegates to page.hover with the correct selector and timeout."""
        page = _page()
        result = hover(page, selector=".menu-item")
        page.hover.assert_called_once_with(".menu-item", timeout=10000)
        assert result["hovered"] == ".menu-item"


class TestSelectOption:
    """Tests for the select_option() interaction tool."""

    def test_select_by_value(self):
        """Test that select_option by value calls page.select_option with the value kwarg."""
        page = _page()
        result = select_option(page, selector="#size", value="large")
        page.select_option.assert_called_once_with(
            "#size", value="large", timeout=10000
        )
        assert result["value"] == "large"

    def test_select_by_label(self):
        """Test that select_option by label calls page.select_option with the label kwarg."""
        page = _page()
        result = select_option(page, selector="#size", label="Large")
        page.select_option.assert_called_once_with(
            "#size", label="Large", timeout=10000
        )
        assert result["label"] == "Large"

    def test_select_no_args_returns_error(self):
        """Test that select_option with neither value nor label returns an error dict."""
        page = _page()
        result = select_option(page, selector="#size")
        assert "error" in result


class TestDragAndDrop:
    """Tests for the drag_and_drop() interaction tool."""

    def test_drag_and_drop_calls_page(self):
        """Test that drag_and_drop delegates to page.drag_and_drop with source and target."""
        page = _page()
        result = drag_and_drop(page, source="#item", target="#slot")
        page.drag_and_drop.assert_called_once_with(
            "#item", "#slot", timeout=10000
        )
        assert result["dragged"] == "#item"
        assert result["to"] == "#slot"
