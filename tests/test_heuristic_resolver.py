"""Tests for the heuristic_resolver package."""

from unittest.mock import MagicMock, patch

from browsegenie.core.browser_agent.heuristic_resolver import (
    KNOWN_TARGETS,
    resolve,
)


def _make_page(found_selector=None):
    """Return a mock Page. If found_selector is given, query_selector_all returns one mock element."""
    page = MagicMock()
    if found_selector is not None:
        elem = MagicMock()
        elem.is_visible.return_value = True
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
    else:
        page.query_selector_all.return_value = []
        page.query_selector.return_value = None
    return page


class TestKnownTargets:
    """Test cases for the KNOWN_TARGETS list exposed by the heuristic_resolver package."""

    def test_known_targets_is_nonempty_list(self):
        """Test that KNOWN_TARGETS is a non-empty list."""
        assert isinstance(KNOWN_TARGETS, list)
        assert len(KNOWN_TARGETS) > 0

    def test_known_targets_sorted(self):
        """Test that KNOWN_TARGETS is sorted alphabetically for stable prompt injection."""
        assert KNOWN_TARGETS == sorted(KNOWN_TARGETS)

    def test_expected_targets_present(self):
        """Test that the core semantic target names are present in KNOWN_TARGETS."""
        expected = [
            "search_input", "username_field", "password_field",
            "submit_button", "results_list", "email_body",
        ]
        for target in expected:
            assert target in KNOWN_TARGETS, f"'{target}' should be in KNOWN_TARGETS"

    def test_aliases_present(self):
        """Test that convenience aliases are present in KNOWN_TARGETS."""
        assert "email_field" in KNOWN_TARGETS     # alias for username_field
        assert "login_button" in KNOWN_TARGETS    # alias for submit_button
        assert "search_results" in KNOWN_TARGETS  # alias for results_list


class TestResolveFunction:
    """Test cases for the public resolve() entry point."""

    def test_unregistered_target_returns_none(self):
        """Test that resolving an unknown target name returns None without raising."""
        page = _make_page()
        result = resolve(page, "totally_unknown_target_xyz")
        assert result is None

    def test_registered_target_invokes_resolver(self):
        """Test that resolving a registered target calls the correct resolver function."""
        page = _make_page()
        import browsegenie.core.browser_agent.heuristic_resolver as hr_module
        original = hr_module._REGISTRY["search_input"]
        try:
            hr_module._REGISTRY["search_input"] = lambda p: "#search"
            result = resolve(page, "search_input")
            assert result == "#search"
        finally:
            hr_module._REGISTRY["search_input"] = original

    def test_resolver_returns_none_when_all_strategies_fail(self):
        """Test that resolve() returns None when the resolver function finds no matching element."""
        page = _make_page(found_selector=None)
        with patch(
            "browsegenie.core.browser_agent.heuristic_resolver._search_input",
            return_value=None,
        ):
            result = resolve(page, "search_input")
        assert result is None

    def test_all_known_targets_have_resolver(self):
        """Test that every entry in KNOWN_TARGETS can be resolved without raising an error."""
        page = _make_page(found_selector=None)
        for target in KNOWN_TARGETS:
            result = resolve(page, target)
            assert result is None or isinstance(result, str)


class TestIndividualResolvers:
    """Smoke-test each resolver module to verify it handles mock pages without raising."""

    def _visible_elem(self, selector_value="input[type=search]"):
        """Return a mock visible element with a selector value."""
        elem = MagicMock()
        elem.is_visible.return_value = True
        elem.get_attribute.return_value = selector_value
        return elem

    def _page_with_elements(self, elems):
        """Return a mock page configured to return the given elements."""
        page = MagicMock()
        page.query_selector_all.return_value = elems
        page.query_selector.return_value = elems[0] if elems else None
        page.evaluate.return_value = "input[type=search]"
        return page

    def test_search_input_found(self):
        """Test that search_input resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.search_input import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "input[type=search]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_search_input_not_found(self):
        """Test that search_input resolver returns None when no matching element exists."""
        from browsegenie.core.browser_agent.heuristic_resolver.search_input import resolve as r
        page = MagicMock()
        page.query_selector_all.return_value = []
        page.query_selector.return_value = None
        page.evaluate.return_value = None
        result = r(page)
        assert result is None

    def test_password_field_found(self):
        """Test that password_field resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.password_field import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "input[type=password]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_submit_button_found(self):
        """Test that submit_button resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.submit_button import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "button[type=submit]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_username_field_found(self):
        """Test that username_field resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.username_field import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "input[name=username]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_text_input_found(self):
        """Test that text_input resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.text_input import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "input[type=text]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_email_to_field_found(self):
        """Test that email_to_field resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.email_to_field import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "input[name=to]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_email_subject_found(self):
        """Test that email_subject resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.email_subject import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "input[name=subject]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_email_body_found(self):
        """Test that email_body resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.email_body import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "div[role=textbox]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_compose_button_found(self):
        """Test that compose_button resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.compose_button import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "div[role=button]"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_results_list_found(self):
        """Test that results_list resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.results_list import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "ul.results"
        result = r(page)
        assert result is None or isinstance(result, str)

    def test_video_card_found(self):
        """Test that video_card resolver returns a string or None without raising."""
        from browsegenie.core.browser_agent.heuristic_resolver.video_card import resolve as r
        page = MagicMock()
        elem = self._visible_elem()
        page.query_selector_all.return_value = [elem]
        page.query_selector.return_value = elem
        page.evaluate.return_value = "ytd-video-renderer"
        result = r(page)
        assert result is None or isinstance(result, str)
