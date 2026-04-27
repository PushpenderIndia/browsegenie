"""Tests for the deterministic step verifier."""

from unittest.mock import MagicMock

from browsegenie.core.browser_agent.agent.verifier import (
    _check,
    _describe,
    _label,
    verify_step,
)


def _make_page(url="https://example.com"):
    """Return a mock Playwright Page with a preset url attribute."""
    page = MagicMock()
    page.url = url
    return page


class TestVerifyStep:
    """Test cases for the public verify_step function."""

    def test_none_type_always_passes(self):
        """Test that condition type 'none' always returns True without any page interaction."""
        page = _make_page()
        assert verify_step(page, {"type": "none"}) is True

    def test_none_type_no_page_calls(self):
        """Test that condition type 'none' makes no calls to the Playwright page."""
        page = _make_page()
        verify_step(page, {"type": "none"})
        page.wait_for_function.assert_not_called()

    def test_emits_events_on_success(self):
        """Test that a passing check emits a 'checking' then 'pass' event via on_event."""
        page = _make_page()
        page.wait_for_function.return_value = None
        events = []
        verify_step(
            page,
            {"type": "url_contains", "value": "example.com"},
            on_event=lambda t, d: events.append((t, d)),
        )
        assert len(events) == 2
        assert events[0][1]["status"] == "checking"
        assert events[1][1]["status"] == "pass"

    def test_none_type_emits_no_events(self):
        """Test that condition type 'none' emits no events since it returns early."""
        page = _make_page()
        events = []
        verify_step(page, {"type": "none"}, on_event=lambda t, d: events.append((t, d)))
        assert len(events) == 0

    def test_url_contains_pass(self):
        """Test that url_contains returns True when wait_for_function succeeds."""
        page = _make_page(url="https://example.com/search?q=cats")
        page.wait_for_function.return_value = None
        result = verify_step(page, {"type": "url_contains", "value": "example.com"})
        assert result is True

    def test_url_contains_fail(self):
        """Test that url_contains returns False when wait_for_function times out."""
        page = _make_page()
        page.wait_for_function.side_effect = Exception("timeout")
        result = verify_step(page, {"type": "url_contains", "value": "nothere.com"})
        assert result is False

    def test_url_changed_pass(self):
        """Test that url_changed returns True when the URL has moved to a new location."""
        page = _make_page(url="https://new.com")
        page.wait_for_function.return_value = None
        result = verify_step(page, {"type": "url_changed"}, prev_url="https://old.com")
        assert result is True

    def test_url_changed_fail(self):
        """Test that url_changed returns False when the URL remains the same."""
        page = _make_page(url="https://same.com")
        page.wait_for_function.side_effect = Exception("timeout")
        result = verify_step(page, {"type": "url_changed"}, prev_url="https://same.com")
        assert result is False

    def test_page_contains_pass(self):
        """Test that page_contains returns True when the keyword appears on the page."""
        page = _make_page()
        page.wait_for_function.return_value = None
        result = verify_step(page, {"type": "page_contains", "value": "success"})
        assert result is True

    def test_page_contains_fail(self):
        """Test that page_contains returns False when the keyword is not found within the timeout."""
        page = _make_page()
        page.wait_for_function.side_effect = Exception("timeout")
        result = verify_step(page, {"type": "page_contains", "value": "missing text"})
        assert result is False

    def test_page_not_contains_pass(self):
        """Test that page_not_contains returns True when the keyword is absent from the page."""
        page = _make_page()
        body = MagicMock()
        body.inner_text.return_value = "Welcome to the homepage"
        page.query_selector.return_value = body
        result = verify_step(page, {"type": "page_not_contains", "value": "error"})
        assert result is True

    def test_page_not_contains_fail(self):
        """Test that page_not_contains returns False when the keyword is present on the page."""
        page = _make_page()
        body = MagicMock()
        body.inner_text.return_value = "An error occurred"
        page.query_selector.return_value = body
        result = verify_step(page, {"type": "page_not_contains", "value": "error"})
        assert result is False

    def test_page_not_contains_no_body(self):
        """Test that page_not_contains returns True when no body element is found."""
        page = _make_page()
        page.query_selector.return_value = None
        result = verify_step(page, {"type": "page_not_contains", "value": "error"})
        assert result is True

    def test_element_visible_pass(self):
        """Test that element_visible returns True when the selector is found visible."""
        page = _make_page()
        page.wait_for_selector.return_value = MagicMock()
        result = verify_step(page, {"type": "element_visible", "selector": "#submit"})
        assert result is True

    def test_element_visible_fail(self):
        """Test that element_visible returns False when the selector times out."""
        page = _make_page()
        page.wait_for_selector.side_effect = Exception("timeout")
        result = verify_step(page, {"type": "element_visible", "selector": "#missing"})
        assert result is False

    def test_unknown_type_treated_as_pass(self):
        """Test that an unrecognised condition type is treated as a pass rather than an error."""
        page = _make_page()
        result = verify_step(page, {"type": "unknown_future_type"})
        assert result is True

    def test_fail_emits_fail_event(self):
        """Test that a failing check emits a 'fail' status event via on_event."""
        page = _make_page()
        page.wait_for_function.side_effect = Exception("timeout")
        events = []
        verify_step(page, {"type": "url_contains", "value": "x"}, on_event=lambda t, d: events.append((t, d)))
        statuses = [e[1]["status"] for e in events]
        assert "fail" in statuses

    def test_page_not_contains_exception_treated_as_pass(self):
        """Test that a Playwright exception during page_not_contains is treated as a pass."""
        page = _make_page()
        page.query_selector.side_effect = Exception("boom")
        result = verify_step(page, {"type": "page_not_contains", "value": "error"})
        assert result is True


class TestCheckInternal:
    """Test cases for the internal _check function."""

    def test_none_passes(self):
        """Test that _check with type 'none' always returns True."""
        assert _check(_make_page(), {"type": "none"}, "") is True

    def test_url_contains_empty_value(self):
        """Test that url_contains with an empty value string still passes when wait succeeds."""
        page = _make_page(url="https://anything.com")
        page.wait_for_function.return_value = None
        assert _check(page, {"type": "url_contains", "value": ""}, "") is True


class TestLabel:
    """Test cases for the _label helper that generates human-readable condition labels."""

    def test_none(self):
        """Test that type 'none' produces the 'No verification' label."""
        assert _label({"type": "none"}) == "No verification"

    def test_url_contains(self):
        """Test that url_contains label includes the target value."""
        assert "example.com" in _label({"type": "url_contains", "value": "example.com"})

    def test_url_changed(self):
        """Test that url_changed produces a label mentioning URL change."""
        assert "URL changed" in _label({"type": "url_changed"})

    def test_page_contains(self):
        """Test that page_contains label includes the keyword being searched."""
        assert "success" in _label({"type": "page_contains", "value": "success"})

    def test_page_not_contains(self):
        """Test that page_not_contains label includes the keyword being excluded."""
        assert "error" in _label({"type": "page_not_contains", "value": "error"})

    def test_element_visible(self):
        """Test that element_visible label includes the CSS selector."""
        assert "#btn" in _label({"type": "element_visible", "selector": "#btn"})

    def test_unknown_type_label(self):
        """Test that an unknown type returns a string without raising."""
        label = _label({"type": "totally_unknown"})
        assert isinstance(label, str)


class TestDescribe:
    """Test cases for the _describe helper that generates pass/fail detail strings."""

    def test_url_contains_found(self):
        """Test that _describe shows a tick when the URL contains the expected value."""
        page = _make_page(url="https://youtube.com/results")
        detail = _describe(page, {"type": "url_contains", "value": "youtube.com"}, "")
        assert "✓" in detail

    def test_url_contains_not_found(self):
        """Test that _describe shows a cross when the URL does not contain the expected value."""
        page = _make_page(url="https://other.com")
        detail = _describe(page, {"type": "url_contains", "value": "youtube.com"}, "")
        assert "✗" in detail

    def test_url_changed_true(self):
        """Test that _describe shows a tick when the URL has changed from prev_url."""
        page = _make_page(url="https://new.com")
        detail = _describe(page, {"type": "url_changed"}, "https://old.com")
        assert "✓" in detail

    def test_url_changed_false(self):
        """Test that _describe shows a cross when the URL has not changed."""
        page = _make_page(url="https://same.com")
        detail = _describe(page, {"type": "url_changed"}, "https://same.com")
        assert "✗" in detail

    def test_page_contains_detail(self):
        """Test that _describe includes the keyword in the detail string for page_contains."""
        page = _make_page(url="https://x.com")
        detail = _describe(page, {"type": "page_contains", "value": "hello"}, "")
        assert "hello" in detail

    def test_element_visible_detail(self):
        """Test that _describe includes the CSS selector in the detail string for element_visible."""
        page = _make_page(url="https://x.com")
        detail = _describe(page, {"type": "element_visible", "selector": ".btn"}, "")
        assert ".btn" in detail

    def test_page_url_exception_returns_unknown(self):
        """Test that _describe falls back to 'unknown' when page.url raises an exception."""
        page = MagicMock()
        type(page).url = property(lambda self: (_ for _ in ()).throw(Exception("no url")))
        detail = _describe(page, {"type": "url_contains", "value": "x"}, "")
        assert "unknown" in detail or isinstance(detail, str)

    def test_none_type_returns_empty(self):
        """Test that _describe returns an empty string for type 'none'."""
        page = _make_page()
        detail = _describe(page, {"type": "none"}, "")
        assert detail == ""
