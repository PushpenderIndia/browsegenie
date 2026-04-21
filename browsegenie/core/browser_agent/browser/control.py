"""
Unified control layer for agent and human browser actions.

Design
------
Human actions are enqueued via `enqueue_human()` (called from the REST handler)
and flushed by the agent loop between steps via `flush()`.  This keeps all
Playwright access on a single thread and avoids concurrent page interaction.

Modes
-----
* shared (default) — both agent and human can act
* agent-only       — human enqueue calls are rejected
* human-only       — agent skips tool-call execution (but still runs LLM)
"""

import queue
import threading
from typing import Any, Dict, List

AGENT_ONLY = "agent-only"
HUMAN_ONLY = "human-only"
SHARED     = "shared"

_VALID_MODES   = {AGENT_ONLY, HUMAN_ONLY, SHARED}
_VALID_ACTIONS = {"click", "type", "press_key", "navigate", "scroll"}


class ControlLayer:
    def __init__(self, mode: str = SHARED) -> None:
        if mode not in _VALID_MODES:
            raise ValueError(f"Invalid mode: {mode!r}")
        self._mode  = mode
        self._lock  = threading.Lock()
        self._queue: queue.Queue = queue.Queue()

    # ── Mode ──────────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        if mode not in _VALID_MODES:
            raise ValueError(f"Invalid mode: {mode!r}")
        with self._lock:
            self._mode = mode

    # ── Human side ────────────────────────────────────────────────────────

    def enqueue_human(self, action: str, payload: Dict[str, Any]) -> Dict:
        """
        Queue a human control action.  Returns immediately (non-blocking).
        Called from the Flask request thread.
        """
        with self._lock:
            mode = self._mode
        if mode == AGENT_ONLY:
            return {"status": "blocked", "reason": "agent-only mode is active"}
        if action not in _VALID_ACTIONS:
            return {"status": "error",   "reason": f"unknown action '{action}'"}
        self._queue.put_nowait({"source": "human", "action": action, "payload": payload})
        return {"status": "queued"}

    # ── Agent side ────────────────────────────────────────────────────────

    def agent_can_act(self) -> bool:
        """False when in human-only mode; the agent should skip tool execution."""
        with self._lock:
            return self._mode != HUMAN_ONLY

    def flush(self, session) -> List[Dict]:
        """
        Execute all pending human actions against *session*.
        Called by the agent loop between steps — no concurrent Playwright access.
        Returns a list of executed action records for event emission.
        """
        executed: List[Dict] = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            result = _dispatch(session, item["action"], item["payload"])
            executed.append({**item, "result": result})
        return executed


# ── Dispatcher ────────────────────────────────────────────────────────────

def _dispatch(session, action: str, payload: Dict[str, Any]) -> Dict:
    """Execute one action against a BrowserSession instance."""
    try:
        if action == "click":
            session.click_xy(float(payload["x"]), float(payload["y"]))
        elif action == "type":
            session.type_text(str(payload["text"]))
        elif action == "press_key":
            session.press_key_str(str(payload["key"]))
        elif action == "navigate":
            session.navigate_to(str(payload["url"]))
        elif action == "scroll":
            session.scroll_wheel(float(payload.get("dx", 0)), float(payload.get("dy", 0)))
        else:
            return {"status": "error", "reason": f"unknown action '{action}'"}
        return {"status": "ok"}
    except KeyError as exc:
        return {"status": "error", "reason": f"missing field {exc}"}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}
