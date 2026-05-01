"""Tests for BrowserAgentSession and module-level session registry in sessions.py."""

import queue

from unittest.mock import MagicMock

from browsegenie.core.browser_agent.agent.sessions import (
    BrowserAgentSession,
    get_session,
)
import browsegenie.core.browser_agent.agent.sessions as _sessions_module


def _make_agent(should_raise=False):
    """Return a mock BrowserAgent that finishes instantly (optionally raising)."""
    agent = MagicMock()
    agent.event_queue = queue.Queue()
    agent.recorder = MagicMock()
    agent.recorder.to_list.return_value = []
    agent.control = MagicMock()
    agent.control.mode = "shared"
    if should_raise:
        agent.run.side_effect = Exception("agent crash")
    else:
        agent.run.return_value = None
    return agent


class TestBrowserAgentSession:
    """Tests for BrowserAgentSession lifecycle and delegation methods."""

    def test_start_executes_agent_run(self):
        """Test that start() calls agent.run() in a daemon thread and signals done."""
        agent = _make_agent()
        session = BrowserAgentSession(agent)
        session.start()
        session.done.wait(timeout=2.0)
        agent.run.assert_called_once()

    def test_is_done_after_run_completes(self):
        """Test that is_done returns True after the agent thread finishes successfully."""
        agent = _make_agent()
        session = BrowserAgentSession(agent)
        session.start()
        session.done.wait(timeout=2.0)
        assert session.is_done is True

    def test_is_done_after_agent_exception(self):
        """Test that is_done is True even when agent.run() raises an exception."""
        agent = _make_agent(should_raise=True)
        session = BrowserAgentSession(agent)
        session.start()
        session.done.wait(timeout=2.0)
        assert session.is_done is True

    def test_stop_calls_agent_stop_and_marks_done(self):
        """Test that stop() calls agent.stop() and sets the done event."""
        agent = _make_agent()
        session = BrowserAgentSession(agent)
        session.stop()
        agent.stop.assert_called_once()
        assert session.is_done is True

    def test_get_playback_frames_delegates_to_recorder(self):
        """Test that get_playback_frames() returns the list from agent.recorder.to_list()."""
        agent = _make_agent()
        agent.recorder.to_list.return_value = [{"index": 0}]
        session = BrowserAgentSession(agent)
        assert session.get_playback_frames() == [{"index": 0}]

    def test_event_queue_property_returns_agent_queue(self):
        """Test that the event_queue property proxies directly to the agent's queue."""
        agent = _make_agent()
        session = BrowserAgentSession(agent)
        assert session.event_queue is agent.event_queue

    def test_execute_control_delegates_to_control_layer(self):
        """Test that execute_control passes action and payload to agent.control.enqueue_human."""
        agent = _make_agent()
        agent.control.enqueue_human.return_value = {"status": "queued"}
        session = BrowserAgentSession(agent)
        result = session.execute_control("click", {"x": 10})
        agent.control.enqueue_human.assert_called_once_with("click", {"x": 10})
        assert result["status"] == "queued"

    def test_get_mode_delegates_to_control_mode(self):
        """Test that get_mode() returns the control layer's mode attribute."""
        agent = _make_agent()
        agent.control.mode = "agent_only"
        session = BrowserAgentSession(agent)
        assert session.get_mode() == "agent_only"

    def test_set_mode_delegates_to_control_set_mode(self):
        """Test that set_mode() calls agent.control.set_mode with the given mode string."""
        agent = _make_agent()
        session = BrowserAgentSession(agent)
        session.set_mode("human_only")
        agent.control.set_mode.assert_called_once_with("human_only")

    def test_session_id_is_unique(self):
        """Test that two BrowserAgentSession instances receive different session IDs."""
        a = BrowserAgentSession(_make_agent())
        b = BrowserAgentSession(_make_agent())
        assert a.session_id != b.session_id


class TestSessionRegistry:
    """Tests for the module-level create_session / get_session registry."""

    def setup_method(self):
        """Clear the global _sessions dict before each test to prevent cross-test pollution."""
        _sessions_module._sessions.clear()

    def test_get_session_missing_returns_none(self):
        """Test that get_session returns None for an unregistered session ID."""
        assert get_session("nonexistent-id") is None

    def test_get_session_after_manual_insert(self):
        """Test that a session manually added to _sessions is retrievable by its ID."""
        agent = _make_agent()
        session = BrowserAgentSession(agent)
        _sessions_module._sessions[session.session_id] = session
        assert get_session(session.session_id) is session
