"""Tests for HistoryManager."""

from browsegenie.core.browser_agent.agent.history import HistoryManager


class TestHistoryManager:
    """Test cases for the HistoryManager class."""

    def setup_method(self):
        """Set up a fresh HistoryManager for each test."""
        self.hm = HistoryManager()

    def test_initial_state(self):
        """Test that a new HistoryManager has an empty message list."""
        assert self.hm.get() == []

    def test_add_system(self):
        """Test that add_system appends a role=system message."""
        self.hm.add_system("You are helpful.")
        msgs = self.hm.get()
        assert len(msgs) == 1
        assert msgs[0] == {"role": "system", "content": "You are helpful."}

    def test_add_initial(self):
        """Test that add_initial appends a role=user message containing the task."""
        self.hm.add_initial("Task: search for cats")
        msgs = self.hm.get()
        assert msgs[0]["role"] == "user"
        assert "Task: search for cats" in msgs[0]["content"]

    def test_add_assistant(self):
        """Test that add_assistant appends the message dict verbatim."""
        msg = {"role": "assistant", "content": "I will click the button"}
        self.hm.add_assistant(msg)
        assert self.hm.get()[0] == msg

    def test_set_step(self):
        """Test that set_step updates the internal step counter."""
        self.hm.set_step(5)
        assert self.hm._step == 5

    def test_add_page_state(self):
        """Test that add_page_state appends a user message with the current state."""
        self.hm.set_step(1)
        self.hm.add_page_state("URL: https://example.com\nSome content here")
        msgs = self.hm.get()
        assert len(msgs) == 1
        assert "Current state:" in msgs[0]["content"]
        assert msgs[0]["role"] == "user"

    def test_add_tool_result_normal(self):
        """Test that add_tool_result appends a role=tool message with the correct call id."""
        self.hm.set_step(1)
        self.hm.add_tool_result("call_1", '{"status": "ok"}', tool="click")
        msgs = self.hm.get()
        assert msgs[0]["role"] == "tool"
        assert msgs[0]["tool_call_id"] == "call_1"
        assert '{"status": "ok"}' in msgs[0]["content"]

    def test_add_tool_result_error(self):
        """Test that an error tool result is returned in full at the current step."""
        self.hm.set_step(1)
        self.hm.add_tool_result("call_2", '{"error": "element not found"}', tool="click")
        msgs = self.hm.get()
        assert '{"error": "element not found"}' in msgs[0]["content"]

    # ── Compression logic ────────────────────────────────────────────────────

    def test_state_compressed_after_state_keep_steps(self):
        """Test that page-state messages older than STATE_KEEP_STEPS are replaced by a summary."""
        self.hm.add_system("sys")
        self.hm.set_step(1)
        self.hm.add_page_state("URL: https://old.com\nOld content")
        self.hm.set_step(5)
        msgs = self.hm.get()
        state_msgs = [m for m in msgs if m.get("role") == "user"]
        assert len(state_msgs) == 1
        assert "[step 1 — URL: https://old.com]" in state_msgs[0]["content"]

    def test_state_not_compressed_within_keep_steps(self):
        """Test that recent page-state messages are returned in full."""
        self.hm.set_step(1)
        self.hm.add_page_state("URL: https://current.com\nCurrent content")
        self.hm.set_step(2)
        msgs = self.hm.get()
        assert "Current state:" in msgs[0]["content"]

    def test_tool_result_truncated_after_tool_keep_steps(self):
        """Test that long tool results older than TOOL_KEEP_STEPS are truncated."""
        long_content = "x" * 1000
        self.hm.set_step(1)
        self.hm.add_tool_result("call_x", long_content, tool="get_page_content")
        self.hm.set_step(5)
        msgs = self.hm.get()
        assert "[truncated]" in msgs[0]["content"]
        assert len(msgs[0]["content"]) < 600

    def test_tool_result_not_truncated_within_keep_steps(self):
        """Test that tool results within TOOL_KEEP_STEPS are returned in full."""
        long_content = "x" * 1000
        self.hm.set_step(1)
        self.hm.add_tool_result("call_x", long_content)
        self.hm.set_step(2)
        msgs = self.hm.get()
        assert "[truncated]" not in msgs[0]["content"]

    def test_error_tool_result_compressed_after_one_step(self):
        """Test that error tool results are compressed to a one-liner after age > 0."""
        self.hm.set_step(3)
        self.hm.add_tool_result("call_err", '{"error": "timeout"}', tool="click")
        self.hm.set_step(4)
        msgs = self.hm.get()
        assert "failed" in msgs[0]["content"]
        assert '{"error": "timeout"}' not in msgs[0]["content"]

    def test_system_and_initial_never_compressed(self):
        """Test that system and initial messages are always returned verbatim."""
        self.hm.add_system("system message")
        self.hm.add_initial("initial task")
        self.hm.set_step(100)
        msgs = self.hm.get()
        assert any(m["content"] == "system message" for m in msgs)
        assert any("initial task" in m["content"] for m in msgs)

    def test_assistant_never_compressed(self):
        """Test that assistant messages are never modified regardless of step age."""
        self.hm.set_step(1)
        msg = {"role": "assistant", "content": "doing something"}
        self.hm.add_assistant(msg)
        self.hm.set_step(100)
        msgs = self.hm.get()
        assert msgs[0] == msg

    # ── _classify ────────────────────────────────────────────────────────────

    def test_classify_json_error(self):
        """Test that a JSON payload with an error key is classified as an error."""
        is_error, summary = self.hm._classify('{"error": "bad selector"}', "click")
        assert is_error is True
        assert "failed" in summary

    def test_classify_non_json_error(self):
        """Test that a raw string starting with Error: is classified as an error."""
        is_error, summary = self.hm._classify('Error: something went wrong', "navigate")
        assert is_error is True

    def test_classify_normal_result(self):
        """Test that a successful JSON result is classified as non-error."""
        is_error, summary = self.hm._classify('{"status": "ok", "items": [1, 2]}', "find_elements")
        assert is_error is False

    def test_classify_long_content_truncated_in_summary(self):
        """Test that long non-error content has an ellipsis in its summary."""
        long_content = "x" * 200
        is_error, summary = self.hm._classify(long_content, "")
        assert "…" in summary

    def test_classify_error_without_tool_label(self):
        """Test that error classification works correctly when no tool name is provided."""
        is_error, summary = self.hm._classify('{"error": "fail"}', "")
        assert is_error is True
        assert "failed" in summary

    # ── Order of messages preserved ──────────────────────────────────────────

    def test_message_order_preserved(self):
        """Test that messages are returned in the same order they were added."""
        self.hm.add_system("sys")
        self.hm.add_initial("init")
        self.hm.set_step(1)
        self.hm.add_page_state("URL: https://a.com\ncontent")
        self.hm.set_step(2)
        self.hm.add_assistant({"role": "assistant", "content": "act"})
        msgs = self.hm.get()
        roles = [m["role"] for m in msgs]
        assert roles == ["system", "user", "user", "assistant"]
