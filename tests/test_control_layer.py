"""Tests for the ControlLayer (browser/control.py)."""

import pytest

from browsegenie.core.browser_agent.browser.control import (
    AGENT_ONLY,
    HUMAN_ONLY,
    SHARED,
    ControlLayer,
)


class TestControlLayerInit:
    """Test cases for ControlLayer initialisation."""

    def test_default_mode_is_shared(self):
        """Test that ControlLayer defaults to SHARED mode."""
        ctrl = ControlLayer()
        assert ctrl.mode == SHARED

    def test_explicit_mode_set(self):
        """Test that an explicit mode is stored correctly on construction."""
        ctrl = ControlLayer(mode=AGENT_ONLY)
        assert ctrl.mode == AGENT_ONLY

    def test_invalid_mode_raises(self):
        """Test that constructing with an unrecognised mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid mode"):
            ControlLayer(mode="superuser")


class TestControlLayerMode:
    """Test cases for mode switching via set_mode."""

    def test_set_mode_shared(self):
        """Test that set_mode can switch from AGENT_ONLY to SHARED."""
        ctrl = ControlLayer(mode=AGENT_ONLY)
        ctrl.set_mode(SHARED)
        assert ctrl.mode == SHARED

    def test_set_mode_human_only(self):
        """Test that set_mode can switch to HUMAN_ONLY."""
        ctrl = ControlLayer()
        ctrl.set_mode(HUMAN_ONLY)
        assert ctrl.mode == HUMAN_ONLY

    def test_set_invalid_mode_raises(self):
        """Test that set_mode raises ValueError for an unrecognised mode string."""
        ctrl = ControlLayer()
        with pytest.raises(ValueError):
            ctrl.set_mode("invalid")


class TestEnqueueHuman:
    """Test cases for the enqueue_human method."""

    def test_queues_valid_action_in_shared_mode(self):
        """Test that a valid action is queued and returns status 'queued' in SHARED mode."""
        ctrl = ControlLayer(mode=SHARED)
        result = ctrl.enqueue_human("click", {"x": 100, "y": 200})
        assert result["status"] == "queued"

    def test_blocked_in_agent_only_mode(self):
        """Test that human actions are blocked when in AGENT_ONLY mode."""
        ctrl = ControlLayer(mode=AGENT_ONLY)
        result = ctrl.enqueue_human("click", {})
        assert result["status"] == "blocked"
        assert "agent-only" in result["reason"]

    def test_unknown_action_returns_error(self):
        """Test that an unrecognised action name returns an error status."""
        ctrl = ControlLayer(mode=SHARED)
        result = ctrl.enqueue_human("fly", {})
        assert result["status"] == "error"
        assert "unknown action" in result["reason"]

    def test_human_only_mode_allows_enqueue(self):
        """Test that human actions are still accepted in HUMAN_ONLY mode."""
        ctrl = ControlLayer(mode=HUMAN_ONLY)
        result = ctrl.enqueue_human("navigate", {"url": "https://x.com"})
        assert result["status"] == "queued"

    def test_all_valid_actions_accepted(self):
        """Test that all registered action names are accepted in SHARED mode."""
        ctrl = ControlLayer(mode=SHARED)
        for action in ["click", "type", "press_key", "navigate", "scroll"]:
            result = ctrl.enqueue_human(action, {})
            assert result["status"] == "queued", f"Action '{action}' should be queued"


class TestAgentCanAct:
    """Test cases for the agent_can_act method."""

    def test_shared_agent_can_act(self):
        """Test that the agent can act in SHARED mode."""
        ctrl = ControlLayer(mode=SHARED)
        assert ctrl.agent_can_act() is True

    def test_agent_only_can_act(self):
        """Test that the agent can act in AGENT_ONLY mode."""
        ctrl = ControlLayer(mode=AGENT_ONLY)
        assert ctrl.agent_can_act() is True

    def test_human_only_agent_cannot_act(self):
        """Test that the agent is blocked from acting in HUMAN_ONLY mode."""
        ctrl = ControlLayer(mode=HUMAN_ONLY)
        assert ctrl.agent_can_act() is False


class TestFlush:
    """Test cases for the flush method that drains and executes queued human actions."""

    def test_flush_empty_queue(self):
        """Test that flushing an empty queue returns an empty list."""
        ctrl = ControlLayer()
        executed = ctrl.flush(None)
        assert executed == []

    def test_flush_executes_queued_action(self):
        """Test that flush executes a queued navigate action against the provided session."""
        ctrl = ControlLayer(mode=SHARED)
        ctrl.enqueue_human("navigate", {"url": "https://example.com"})

        session = type("FakeSess", (), {"navigate_to": lambda self, url: None})()
        executed = ctrl.flush(session)
        assert len(executed) == 1
        assert executed[0]["action"] == "navigate"

    def test_flush_executes_multiple_actions_in_order(self):
        """Test that flush executes multiple queued actions in FIFO order."""
        ctrl = ControlLayer(mode=SHARED)
        ctrl.enqueue_human("navigate", {"url": "https://a.com"})
        ctrl.enqueue_human("scroll", {"dx": 0, "dy": 100})

        session = type("FakeSess", (), {
            "navigate_to": lambda self, url: None,
            "scroll_wheel": lambda self, dx, dy: None,
        })()
        executed = ctrl.flush(session)
        assert len(executed) == 2
        assert executed[0]["action"] == "navigate"
        assert executed[1]["action"] == "scroll"

    def test_flush_clears_queue(self):
        """Test that after a flush the queue is empty and a second flush returns nothing."""
        ctrl = ControlLayer(mode=SHARED)
        ctrl.enqueue_human("navigate", {"url": "https://a.com"})

        session = type("FakeSess", (), {"navigate_to": lambda self, url: None})()
        ctrl.flush(session)
        executed_again = ctrl.flush(session)
        assert executed_again == []
