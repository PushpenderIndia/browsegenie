"""Browser automation agent: step loop, tool dispatch, and loop detection."""

import json
import queue
import time
from typing import Any, Dict, Optional

from ..browser.control import ControlLayer, SHARED
from ..browser.session import BrowserSession
from ..playback.recorder import ScreenshotRecorder
from ..tools.registry import schemas_for, run_tool
from .history import HistoryManager
from .llm import LLMClient
from .prompts import SYSTEM_PROMPT, capture_page_state

# Minimum interval between live_frame emissions (seconds). ~10 fps max.
_LIVE_FRAME_MIN_INTERVAL = 0.10


class BrowserAgent:
    # Consecutive steps with an unchanged URL before injecting a recovery hint.
    STUCK_THRESHOLD: int = 3

    def __init__(
        self,
        task: str,
        model: str,
        provider: str = "",
        api_key: Optional[str] = None,
        headless: bool = True,
        max_steps: int = 50,
        control_mode: str = SHARED,
    ) -> None:
        self._task      = task
        self._max_steps = max_steps
        self._headless  = headless
        self._browser   = BrowserSession(headless=headless)
        self._llm       = LLMClient(model=model, provider=provider, api_key=api_key)
        self._queue: queue.Queue = queue.Queue()
        self._recorder  = ScreenshotRecorder()
        self._active    = False
        self._control   = ControlLayer(mode=control_mode)
        # Rate-limiter for live frames
        self._last_live_ts: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def event_queue(self) -> queue.Queue:
        return self._queue

    @property
    def recorder(self) -> ScreenshotRecorder:
        return self._recorder

    @property
    def control(self) -> ControlLayer:
        return self._control

    def stop(self) -> None:
        self._active = False
        self._browser.stop()

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self) -> None:
        self._active = True
        self._browser.start()

        # Start CDP screencast for live browser view
        cdp_ok = self._browser.start_screencast(self._on_live_frame)
        self._emit("connection", {"status": "connected", "cdp": cdp_ok})

        history = HistoryManager()
        history.add_system(SYSTEM_PROMPT)
        history.add_initial(
            f"Task: {self._task}\n\nInitial state:\n{capture_page_state(self._browser)}"
        )

        _last_url: str = ""
        _stuck_steps: int = 0
        _last_tool: Optional[str] = None

        try:
            self._emit("start", {"task": self._task})
            self._emit_screenshot(step=0)

            for step in range(1, self._max_steps + 1):
                if not self._active:
                    break

                # Flush human actions queued since the last step
                self._flush_human_actions()

                history.set_step(step)
                self._emit("step", {"step": step, "status": "thinking"})

                response = self._llm.complete(history.get(), schemas_for(_last_tool))
                self._emit("tokens", self._llm.token_stats())

                msg           = response.choices[0].message
                assistant_msg = self._build_assistant_dict(msg)
                history.add_assistant(assistant_msg)

                if not msg.tool_calls:
                    if msg.content:
                        self._emit("log", {"message": msg.content})
                    break

                # In human-only mode the agent skips actual tool execution
                if not self._control.agent_can_act():
                    self._emit("log", {"message": "[agent-only locked out — human-only mode]"})
                    continue

                finished, _last_tool = self._process_tool_calls(msg.tool_calls, step, history)
                if finished:
                    break

                # Detect stuck loops: URL unchanged for N consecutive steps
                current_url = self._browser.current_url()
                if current_url == _last_url:
                    _stuck_steps += 1
                else:
                    _stuck_steps = 0
                    _last_url = current_url

                state = capture_page_state(self._browser)

                if _stuck_steps >= self.STUCK_THRESHOLD:
                    hint = (
                        f"WARNING: The page URL has not changed for {_stuck_steps} steps "
                        f"(still at {current_url}). You appear to be stuck.\n"
                        "Suggestions:\n"
                        "- If you filled a search box, submit it with press_key(key='Enter') instead of clicking.\n"
                        "- Call get_interactive_elements and read element text carefully before clicking.\n"
                        "- Try navigate() directly to a known URL if you know where to go.\n"
                        "- Do NOT repeat the same action again."
                    )
                    state = hint + "\n\n" + state

                history.add_page_state(state)

            else:
                self._emit_screenshot(step=self._max_steps, tool="done")
                self._emit("done", {
                    "summary":      "Maximum steps reached without completion.",
                    "data":         {},
                    "total_frames": self._recorder.count(),
                })

        except Exception as exc:
            self._emit("error", {"message": str(exc)})
        finally:
            self._active = False
            self._browser.stop_screencast()
            self._emit("connection", {"status": "disconnected"})
            # In non-headless mode the browser window stays open after the task
            # completes so the user can inspect or continue interacting with it.
            # The Stop button calls agent.stop() directly which always closes it.
            if self._headless:
                self._browser.stop()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _flush_human_actions(self) -> None:
        """
        Execute all pending human control actions on the agent thread.

        Playwright's sync API uses greenlet and is bound to the thread that
        created the browser objects.  Human actions MUST be executed on this
        same thread — calling Playwright from any other thread raises
        ``greenlet.error: Cannot switch to a different thread``.

        This is called at the start of each step AND after each individual
        tool call so the maximum wait is one tool execution (~0.5–2 s),
        not a full LLM round-trip (10–30 s).
        """
        for item in self._control.flush(self._browser):
            self._emit("control", item)

    def _process_tool_calls(
        self, tool_calls, step: int, history: HistoryManager
    ) -> tuple[bool, Optional[str]]:
        """Execute each tool call. Returns ``(finished, last_tool_name)``."""
        last_tool: Optional[str] = None

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}

            self._emit("tool_call", {"step": step, "tool": name, "args": args})

            if name == "done":
                self._emit_screenshot(step=step, tool="done")
                self._emit("done", {
                    "summary":      args.get("summary", "Task completed"),
                    "data":         args.get("data") or {},
                    "total_frames": self._recorder.count(),
                })
                history.add_tool_result(tc.id, '{"status":"completed"}', tool="done")
                return True, "done"

            result     = run_tool(self._browser.page, name, args)
            result_str = json.dumps(result)
            self._emit("tool_result", {"step": step, "tool": name, "result": result})
            self._emit_screenshot(step=step, tool=name)
            history.add_tool_result(tc.id, result_str, tool=name)
            last_tool = name

            # Flush human actions between tool calls (agent thread only —
            # Playwright's greenlet model forbids cross-thread page access)
            self._flush_human_actions()

        return False, last_tool

    @staticmethod
    def _build_assistant_dict(msg) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": "assistant"}
        if msg.content:
            d["content"] = msg.content
        if msg.tool_calls:
            d["tool_calls"] = [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        else:
            d.setdefault("content", "")
        return d

    def _emit(self, event_type: str, data: Any) -> None:
        self._queue.put_nowait({"type": event_type, "data": data})

    def _emit_screenshot(self, step: int = 0, tool: str = "") -> None:
        """Capture screenshot and emit as event + record frame for playback."""
        try:
            image = self._browser.screenshot_jpeg_b64()
            url   = self._browser.current_url()
            title = self._browser.page_title()
            frame = self._recorder.record(step=step, tool=tool, url=url, title=title, image_b64=image)
            self._emit("screenshot", {
                "image":        image,
                "url":          url,
                "title":        title,
                "step":         step,
                "tool":         tool,
                "frame_index":  frame.index,
                "total_frames": self._recorder.count(),
            })
        except Exception:
            pass

    def _on_live_frame(self, image_b64: str, metadata: dict) -> None:
        """
        CDP screencast callback — called on Playwright's thread.
        Rate-limited to ~10 fps; must not make blocking Playwright calls.
        """
        now = time.monotonic()
        if now - self._last_live_ts < _LIVE_FRAME_MIN_INTERVAL:
            return
        self._last_live_ts = now

        url = ""
        try:
            url = self._browser.current_url()
        except Exception:
            pass

        self._queue.put_nowait({
            "type": "live_frame",
            "data": {
                "image":     image_b64,
                "url":       url,
                "timestamp": metadata.get("timestamp", now),
            },
        })
