"""Message history manager for the browser agent LLM loop.

Each step appends three entry types:
  - assistant messages  (tool calls chosen by the LLM)
  - tool results        (the output of each browser action)
  - page-state updates  (URL, visible elements, and text snapshot)

Because the full history is re-sent on every LLM call, older entries are
compressed to prevent unbounded token growth:
  - Page-state messages older than STATE_KEEP_STEPS steps are replaced with a
    one-liner: "[step N — URL: https://...]"
  - Tool results older than TOOL_KEEP_STEPS steps are truncated to
    TOOL_RESULT_MAX_CHARS characters.
  - Error results are compressed to a one-liner after just one step — the LLM
    only needs the full Playwright stack trace immediately after it occurs.
  - System, initial-task, and assistant messages are never modified.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class _Kind(Enum):
    SYSTEM    = "system"
    INITIAL   = "initial"
    ASSISTANT = "assistant"
    TOOL      = "tool"
    STATE     = "state"


@dataclass
class _Entry:
    kind:     _Kind
    message:  Dict
    step:     int
    summary:  Optional[str] = None  # compact replacement used when entry is old
    is_error: bool = field(default=False)


class HistoryManager:
    """Maintains the LLM message list and compresses stale entries on read."""

    TOOL_RESULT_MAX_CHARS: int = 500
    TOOL_KEEP_STEPS:       int = 2
    STATE_KEEP_STEPS:      int = 2

    def __init__(self) -> None:
        self._entries: List[_Entry] = []
        self._step: int = 0

    # ── Step tracking ─────────────────────────────────────────────────────────

    def set_step(self, step: int) -> None:
        self._step = step

    # ── Writers ───────────────────────────────────────────────────────────────

    def add_system(self, content: str) -> None:
        self._entries.append(_Entry(
            kind=_Kind.SYSTEM,
            message={"role": "system", "content": content},
            step=0,
        ))

    def add_initial(self, content: str) -> None:
        """First user message: task description + initial page state."""
        self._entries.append(_Entry(
            kind=_Kind.INITIAL,
            message={"role": "user", "content": content},
            step=0,
        ))

    def add_assistant(self, msg: Dict) -> None:
        self._entries.append(_Entry(kind=_Kind.ASSISTANT, message=msg, step=self._step))

    def add_tool_result(self, call_id: str, content: str, tool: str = "") -> None:
        is_error, summary = self._classify(content, tool)
        self._entries.append(_Entry(
            kind=_Kind.TOOL,
            message={"role": "tool", "tool_call_id": call_id, "content": content},
            step=self._step,
            summary=summary,
            is_error=is_error,
        ))

    def add_page_state(self, state: str) -> None:
        first_line = state.split("\n", 1)[0]   # "URL: https://..."
        self._entries.append(_Entry(
            kind=_Kind.STATE,
            message={"role": "user", "content": f"Continuing. Current state:\n{state}"},
            step=self._step,
            summary=f"[step {self._step} — {first_line}]",
        ))

    # ── Reader ────────────────────────────────────────────────────────────────

    def get(self) -> List[Dict]:
        """Return the compressed message list ready to send to the LLM."""
        messages: List[Dict] = []
        for entry in self._entries:
            if entry.kind in (_Kind.SYSTEM, _Kind.INITIAL, _Kind.ASSISTANT):
                messages.append(entry.message)
                continue

            age = self._step - entry.step

            if entry.kind == _Kind.TOOL:
                # Error results: keep full only for the current step so the LLM
                # can react immediately; compress to a one-liner after that.
                # The full Playwright stack trace is never useful two steps later.
                if entry.is_error and age > 0:
                    messages.append({**entry.message, "content": entry.summary})
                elif age > self.TOOL_KEEP_STEPS:
                    body = entry.message["content"]
                    if len(body) > self.TOOL_RESULT_MAX_CHARS:
                        body = body[:self.TOOL_RESULT_MAX_CHARS] + "… [truncated]"
                    messages.append({**entry.message, "content": body})
                else:
                    messages.append(entry.message)

            elif entry.kind == _Kind.STATE:
                if age > self.STATE_KEEP_STEPS:
                    messages.append({"role": "user", "content": entry.summary})
                else:
                    messages.append(entry.message)

        return messages

    # ── Private ───────────────────────────────────────────────────────────────

    def _classify(self, content: str, tool: str) -> tuple:
        """Return (is_error, summary) for a tool result string.

        Primary detection: parse JSON and check for an "error" key.
        Fallback detection: string prefix check for the rare case where the
        content is not valid JSON (e.g. raw exception text from a failed call).
        """
        error_msg = ""

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "error" in parsed:
                error_msg = str(parsed["error"])[:100].replace("\n", " ")
        except (json.JSONDecodeError, Exception):
            # Fallback: catch raw non-JSON error strings
            stripped = content.lstrip()
            if stripped.startswith('{"error"') or stripped.lower().startswith("error"):
                error_msg = stripped[:100].replace("\n", " ")

        if error_msg:
            label = f"{tool}: " if tool else ""
            return True, f"[step {self._step} {label}failed — {error_msg}]"

        preview = content[:120].replace("\n", " ")
        if len(content) > 120:
            preview += "…"
        return False, f"[step {self._step} result: {preview}]"
