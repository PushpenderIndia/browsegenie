"""Tests for the browse() convenience function and _resolve_model_and_provider in browser.py."""

import queue
from unittest.mock import MagicMock, patch

from browsegenie.browser import _resolve_model_and_provider, browse


# ── _resolve_model_and_provider ───────────────────────────────────────────────

class TestResolveModelAndProvider:
    """Tests for the provider auto-detection helper."""

    def test_explicit_provider_passthrough(self):
        """Test that an explicitly supplied provider is returned unchanged."""
        model, prov = _resolve_model_and_provider("my-model", "mycloud")
        assert prov == "mycloud"
        assert model == "my-model"

    def test_gpt_prefix_detects_openai(self):
        """Test that a model starting with 'gpt-' is identified as openai."""
        _, prov = _resolve_model_and_provider("gpt-4o", None)
        assert prov == "openai"

    def test_o1_prefix_detects_openai(self):
        """Test that a model starting with 'o1' is identified as openai."""
        _, prov = _resolve_model_and_provider("o1-mini", None)
        assert prov == "openai"

    def test_o3_prefix_detects_openai(self):
        """Test that a model starting with 'o3' is identified as openai."""
        _, prov = _resolve_model_and_provider("o3-mini", None)
        assert prov == "openai"

    def test_o4_prefix_detects_openai(self):
        """Test that a model starting with 'o4' is identified as openai."""
        _, prov = _resolve_model_and_provider("o4-mini", None)
        assert prov == "openai"

    def test_claude_prefix_detects_anthropic(self):
        """Test that a model starting with 'claude-' is identified as anthropic."""
        _, prov = _resolve_model_and_provider("claude-3-5-sonnet-20241022", None)
        assert prov == "anthropic"

    def test_gemini_prefix_detects_google(self):
        """Test that a model starting with 'gemini-' is identified as google."""
        _, prov = _resolve_model_and_provider("gemini-2.5-flash", None)
        assert prov == "google"

    def test_mistral_prefix_detects_mistral(self):
        """Test that a model starting with 'mistral' is identified as mistral."""
        _, prov = _resolve_model_and_provider("mistral-7b", None)
        assert prov == "mistral"

    def test_deepseek_prefix_detects_deepseek(self):
        """Test that a model starting with 'deepseek' is identified as deepseek."""
        _, prov = _resolve_model_and_provider("deepseek-chat", None)
        assert prov == "deepseek"

    def test_ollama_prefix_detects_ollama(self):
        """Test that a model starting with 'ollama/' is identified as ollama."""
        _, prov = _resolve_model_and_provider("ollama/llama3", None)
        assert prov == "ollama"

    def test_command_prefix_detects_cohere(self):
        """Test that a model starting with 'command' is identified as cohere."""
        _, prov = _resolve_model_and_provider("command-r", None)
        assert prov == "cohere"

    def test_grok_prefix_detects_xai(self):
        """Test that a model starting with 'grok' is identified as xai."""
        _, prov = _resolve_model_and_provider("grok-2", None)
        assert prov == "xai"

    def test_unknown_model_defaults_to_google(self):
        """Test that an unrecognised model name defaults to the google provider."""
        _, prov = _resolve_model_and_provider("some-random-model", None)
        assert prov == "google"


# ── browse() ──────────────────────────────────────────────────────────────────

def _make_session(events=None):
    """Return a mock BrowserAgentSession whose event_queue is pre-populated with events."""
    session = MagicMock()
    q = queue.Queue()
    for ev in (events or []):
        q.put(ev)
    session.event_queue = q
    session.get_playback_frames.return_value = []
    type(session).is_done = property(lambda s: s.event_queue.empty())
    return session


class TestBrowseFunction:
    """Tests for the top-level browse() convenience function."""

    def _session_with_done_event(self):
        """Return a session that emits a single done event."""
        events = [{"type": "done", "data": {"summary": "Task complete", "data": {"k": "v"}}}]
        return _make_session(events=events)

    def test_browse_happy_path_returns_result_dict(self):
        """Test that browse() returns a dict with all expected keys on success."""
        session = self._session_with_done_event()
        with patch("browsegenie.browser.create_session", return_value=session):
            result = browse(
                task="test task",
                api_key="key",
                model_name="gpt-4o",
                show_logs=False,
            )
        assert result["success"] is True
        assert result["summary"] == "Task complete"
        assert result["data"] == {"k": "v"}

    def test_browse_on_event_callback_fired(self):
        """Test that on_event callback is called for each event when supplied."""
        events = [
            {"type": "step", "data": {"step": 1}},
            {"type": "done", "data": {"summary": "done"}},
        ]
        session = _make_session(events=events)
        captured = []
        with patch("browsegenie.browser.create_session", return_value=session):
            browse(
                task="task",
                api_key="k",
                model_name="gpt-4o",
                on_event=lambda t, _d: captured.append(t),
                show_logs=False,
            )
        assert "step" in captured
        assert "done" in captured

    def test_browse_timeout_calls_stop(self):
        """Test that browse() calls session.stop() when the timeout expires."""
        session = _make_session(events=[])
        # Make is_done always False so the timeout fires
        type(session).is_done = property(lambda s: False)  # noqa: ARG005
        with patch("browsegenie.browser.create_session", return_value=session):
            result = browse(
                task="task",
                api_key="k",
                model_name="gpt-4o",
                timeout=0.05,
                show_logs=False,
            )
        session.stop.assert_called()
        assert result["error"] is not None

    def test_browse_error_event_sets_error_key(self):
        """Test that an error event sets result['error'] to the event message."""
        events = [{"type": "error", "data": {"message": "Something went wrong"}}]
        session = _make_session(events=events)
        with patch("browsegenie.browser.create_session", return_value=session):
            result = browse(
                task="task",
                api_key="k",
                model_name="gpt-4o",
                show_logs=False,
            )
        assert result["error"] == "Something went wrong"
        assert result["success"] is False

    def test_browse_step_event_updates_steps(self):
        """Test that step events increment the steps counter in the result."""
        events = [
            {"type": "step", "data": {"step": 3}},
            {"type": "done", "data": {"summary": "ok"}},
        ]
        session = _make_session(events=events)
        with patch("browsegenie.browser.create_session", return_value=session):
            result = browse(
                task="task",
                api_key="k",
                model_name="gpt-4o",
                show_logs=False,
            )
        assert result["steps"] == 3
