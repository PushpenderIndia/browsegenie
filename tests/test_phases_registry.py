"""Tests for tool phases and registry."""

from unittest.mock import MagicMock, patch

from browsegenie.core.browser_agent.tools.phases import schemas_for, PHASE_SCHEMAS, _NEXT_PHASE
from browsegenie.core.browser_agent.tools.registry import run_tool


# ── schemas_for ───────────────────────────────────────────────────────────────

class TestSchemasFor:
    """Test cases for the schemas_for phase-selection function."""

    def test_none_returns_navigate_phase(self):
        """Test that passing None (task start) returns the navigate phase schemas."""
        schemas = schemas_for(None)
        assert schemas is PHASE_SCHEMAS["navigate"]

    def test_navigate_leads_to_read_phase(self):
        """Test that after a navigate tool call, the read phase schemas are returned."""
        assert schemas_for("navigate") is PHASE_SCHEMAS["read"]

    def test_get_page_content_leads_to_interact(self):
        """Test that after reading page content, the interact phase schemas are returned."""
        assert schemas_for("get_page_content") is PHASE_SCHEMAS["interact"]

    def test_find_elements_leads_to_interact(self):
        """Test that after finding elements, the interact phase schemas are returned."""
        assert schemas_for("find_elements") is PHASE_SCHEMAS["interact"]

    def test_click_leads_to_read(self):
        """Test that after a click, the read phase schemas are returned."""
        assert schemas_for("click") is PHASE_SCHEMAS["read"]

    def test_fill_leads_to_interact(self):
        """Test that after filling an input, the interact phase schemas are returned."""
        assert schemas_for("fill") is PHASE_SCHEMAS["interact"]

    def test_press_key_leads_to_read(self):
        """Test that after a key press (e.g. Enter to submit), the read phase schemas are returned."""
        assert schemas_for("press_key") is PHASE_SCHEMAS["read"]

    def test_scroll_leads_to_read(self):
        """Test that after scrolling, the read phase schemas are returned."""
        assert schemas_for("scroll") is PHASE_SCHEMAS["read"]

    def test_wait_for_load_leads_to_read(self):
        """Test that after waiting for page load, the read phase schemas are returned."""
        assert schemas_for("wait_for_load") is PHASE_SCHEMAS["read"]

    def test_unknown_tool_defaults_to_read(self):
        """Test that an unrecognised tool name falls back to the read phase."""
        assert schemas_for("some_unknown_tool") is PHASE_SCHEMAS["read"]

    def test_plan_leads_to_read(self):
        """Test that after a plan step, the read phase schemas are returned."""
        assert schemas_for("plan") is PHASE_SCHEMAS["read"]

    def test_hover_leads_to_interact(self):
        """Test that after a hover action, the interact phase schemas are returned."""
        assert schemas_for("hover") is PHASE_SCHEMAS["interact"]

    def test_execute_js_leads_to_read(self):
        """Test that after executing JavaScript, the read phase schemas are returned."""
        assert schemas_for("execute_js") is PHASE_SCHEMAS["read"]

    def test_go_back_leads_to_read(self):
        """Test that after going back in browser history, the read phase schemas are returned."""
        assert schemas_for("go_back") is PHASE_SCHEMAS["read"]

    def test_schemas_are_nonempty_lists(self):
        """Test that every phase has a non-empty list of schemas."""
        for phase, schemas in PHASE_SCHEMAS.items():
            assert isinstance(schemas, list), f"{phase} schemas should be a list"
            assert len(schemas) > 0, f"{phase} schemas should not be empty"

    def test_all_phases_contain_done(self):
        """Test that the DONE schema is present in every phase so the agent can always terminate."""
        from browsegenie.core.browser_agent.tools.schemas import DONE
        for phase, schemas in PHASE_SCHEMAS.items():
            assert DONE in schemas, f"Phase '{phase}' should always include DONE"

    def test_all_phases_contain_plan(self):
        """Test that the PLAN schema is present in every phase so re-planning is always available."""
        from browsegenie.core.browser_agent.tools.schemas import PLAN
        for phase, schemas in PHASE_SCHEMAS.items():
            assert PLAN in schemas, f"Phase '{phase}' should always include PLAN"

    def test_next_phase_covers_all_dispatch_entries(self):
        """Test that every tool in _NEXT_PHASE maps to a recognised phase name."""
        for tool, phase in _NEXT_PHASE.items():
            assert phase in PHASE_SCHEMAS, f"'{tool}' maps to unknown phase '{phase}'"


# ── run_tool ──────────────────────────────────────────────────────────────────

class TestRunTool:
    """Test cases for the run_tool dispatch function."""

    def _make_page(self):
        """Return a mock Playwright Page object."""
        return MagicMock()

    def test_unknown_tool_returns_error(self):
        """Test that an unregistered tool name returns an error dict without raising."""
        page = self._make_page()
        result = run_tool(page, "nonexistent_tool", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]

    def test_navigate_called(self):
        """Test that the 'navigate' tool dispatches to the navigate handler with correct args."""
        page = self._make_page()
        with patch("browsegenie.core.browser_agent.tools.registry.navigate") as mock_nav:
            mock_nav.return_value = {"status": "navigated"}
            result = run_tool(page, "navigate", {"url": "https://example.com"})
            mock_nav.assert_called_once_with(page, url="https://example.com")
            assert result == {"status": "navigated"}

    def test_click_called(self):
        """Test that the 'click' tool dispatches to the click handler."""
        page = self._make_page()
        with patch("browsegenie.core.browser_agent.tools.registry.click") as mock_click:
            mock_click.return_value = {"status": "clicked"}
            result = run_tool(page, "click", {"selector": "#btn"})
            assert result == {"status": "clicked"}

    def test_fill_called(self):
        """Test that the 'fill' tool dispatches to the fill handler."""
        page = self._make_page()
        with patch("browsegenie.core.browser_agent.tools.registry.fill") as mock_fill:
            mock_fill.return_value = {"status": "filled"}
            result = run_tool(page, "fill", {"selector": "#input", "text": "hello"})
            assert result == {"status": "filled"}

    def test_handler_exception_returns_error_dict(self):
        """Test that an exception raised by a handler is caught and returned as an error dict."""
        page = self._make_page()
        with patch("browsegenie.core.browser_agent.tools.registry.navigate") as mock_nav:
            mock_nav.side_effect = Exception("timeout")
            result = run_tool(page, "navigate", {"url": "https://example.com"})
            assert "error" in result
            assert "timeout" in result["error"]
            assert result["tool"] == "navigate"

    def test_scroll_to_bottom_called(self):
        """Test that 'scroll_to_bottom' dispatches its handler with only the page argument."""
        page = self._make_page()
        with patch("browsegenie.core.browser_agent.tools.registry.scroll_to_bottom") as mock_s:
            mock_s.return_value = {"status": "scrolled"}
            run_tool(page, "scroll_to_bottom", {})
            mock_s.assert_called_once_with(page)

    def test_get_page_content_called(self):
        """Test that 'get_page_content' dispatches its handler with only the page argument."""
        page = self._make_page()
        with patch("browsegenie.core.browser_agent.tools.registry.get_page_content") as mock_gpc:
            mock_gpc.return_value = {"content": "hello"}
            run_tool(page, "get_page_content", {})
            mock_gpc.assert_called_once_with(page)
