"""Tests for the task planner module."""

import json
from unittest.mock import MagicMock

from browsegenie.core.browser_agent.agent.planner import generate_plan


def _make_llm(response_text: str):
    """Return a mock LLMClient that returns response_text from complete_text."""
    llm = MagicMock()
    llm.complete_text.return_value = response_text
    return llm


class TestGeneratePlan:
    """Test cases for the generate_plan function."""

    def test_valid_plan_returned(self):
        """Test that a well-formed LLM response returns a list of step dicts."""
        steps = [
            {"tool": "fill", "args": {"target": "search_input", "text": "cats"}, "verify": {"type": "none"}},
            {"tool": "press_key", "args": {"key": "Enter"}, "verify": {"type": "url_changed"}},
        ]
        llm = _make_llm(json.dumps({"steps": steps}))
        result = generate_plan("search for cats", llm, current_url="https://google.com")
        assert result is not None
        assert len(result) == 2
        assert result[0]["tool"] == "fill"
        assert result[1]["tool"] == "press_key"

    def test_strips_markdown_fences(self):
        """Test that ```json ... ``` fences are stripped before JSON parsing."""
        steps = [{"tool": "navigate", "args": {"url": "https://example.com"}, "verify": {"type": "url_contains", "value": "example.com"}}]
        raw = f"```json\n{json.dumps({'steps': steps})}\n```"
        llm = _make_llm(raw)
        result = generate_plan("go to example.com", llm)
        assert result is not None
        assert len(result) == 1

    def test_strips_plain_markdown_fences(self):
        """Test that plain ``` ... ``` fences (without json tag) are stripped."""
        steps = [{"tool": "click", "args": {"target": "submit_button"}, "verify": {"type": "none"}}]
        raw = f"```\n{json.dumps({'steps': steps})}\n```"
        llm = _make_llm(raw)
        result = generate_plan("click submit", llm)
        assert result is not None

    def test_empty_steps_returns_none(self):
        """Test that a plan with an empty steps list returns None."""
        llm = _make_llm(json.dumps({"steps": []}))
        result = generate_plan("do something", llm)
        assert result is None

    def test_missing_steps_key_returns_none(self):
        """Test that a JSON response without a steps key returns None."""
        llm = _make_llm(json.dumps({"actions": [{"tool": "click"}]}))
        result = generate_plan("do something", llm)
        assert result is None

    def test_invalid_json_returns_none(self):
        """Test that a non-JSON LLM response returns None without raising."""
        llm = _make_llm("this is not JSON at all")
        result = generate_plan("do something", llm)
        assert result is None

    def test_llm_exception_returns_none(self):
        """Test that an exception from the LLM client returns None gracefully."""
        llm = MagicMock()
        llm.complete_text.side_effect = Exception("network error")
        result = generate_plan("do something", llm)
        assert result is None

    def test_current_url_passed_to_prompt(self):
        """Test that the current_url argument is included in the user prompt sent to the LLM."""
        steps = [{"tool": "navigate", "args": {"url": "https://x.com"}, "verify": {"type": "none"}}]
        llm = _make_llm(json.dumps({"steps": steps}))
        generate_plan("go somewhere", llm, current_url="https://start.com")
        call_args = llm.complete_text.call_args[0][0]
        user_prompt = call_args[1]["content"]
        assert "https://start.com" in user_prompt

    def test_default_current_url_is_unknown(self):
        """Test that omitting current_url inserts 'unknown' as the placeholder."""
        steps = [{"tool": "navigate", "args": {"url": "https://x.com"}, "verify": {"type": "none"}}]
        llm = _make_llm(json.dumps({"steps": steps}))
        generate_plan("go somewhere", llm)
        call_args = llm.complete_text.call_args[0][0]
        user_prompt = call_args[1]["content"]
        assert "unknown" in user_prompt

    def test_known_targets_in_prompt(self):
        """Test that KNOWN_TARGETS are injected into the user prompt so the LLM can reference them."""
        steps = [{"tool": "fill", "args": {"target": "search_input", "text": "hi"}, "verify": {"type": "none"}}]
        llm = _make_llm(json.dumps({"steps": steps}))
        generate_plan("search something", llm)
        call_args = llm.complete_text.call_args[0][0]
        user_prompt = call_args[1]["content"]
        assert "search_input" in user_prompt

    def test_non_list_steps_returns_none(self):
        """Test that a steps value that is not a list returns None."""
        llm = _make_llm(json.dumps({"steps": "not a list"}))
        result = generate_plan("do something", llm)
        assert result is None

    def test_whitespace_stripped_before_parsing(self):
        """Test that leading/trailing whitespace in the LLM response is stripped before parsing."""
        steps = [{"tool": "click", "args": {"target": "submit_button"}, "verify": {"type": "none"}}]
        llm = _make_llm("  " + json.dumps({"steps": steps}) + "  ")
        result = generate_plan("click submit", llm)
        assert result is not None
