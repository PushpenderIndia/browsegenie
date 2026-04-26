"""Browser automation agent: step loop, tool dispatch, and loop detection."""

import json
import logging
import queue
import time
from typing import Any, Dict, List, Optional

from ..browser.control import ControlLayer, SHARED
from ..browser.session import BrowserSession
from ..heuristic_resolver import resolve as heuristic_resolve, KNOWN_TARGETS
from ..playback.recorder import ScreenshotRecorder
from ..tools.registry import schemas_for, run_tool
from .history import HistoryManager
from .llm import LLMClient
from .planner import generate_plan
from .prompts import SYSTEM_PROMPT, capture_page_state
from .verifier import verify_step

logger = logging.getLogger(__name__)

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

    # ── Main entry point ─────────────────────────────────────────────────

    def run(self) -> None:
        self._active = True
        self._browser.start()

        cdp_ok = self._browser.start_screencast(self._on_live_frame)
        self._emit("connection", {"status": "connected", "cdp": cdp_ok})

        history = HistoryManager()
        history.add_system(SYSTEM_PROMPT)
        history.add_initial(
            f"Task: {self._task}\n\nInitial state:\n{capture_page_state(self._browser)}"
        )

        try:
            self._emit("start", {"task": self._task})
            self._emit_screenshot(step=0)

            # Single unified loop — AI calls plan() first, then recovers manually if needed
            self._run_agent_loop(history)

        except Exception as exc:
            self._emit("error", {"message": str(exc)})
        finally:
            self._active = False
            self._browser.stop_screencast()
            self._emit("connection", {"status": "disconnected"})
            if self._headless:
                self._browser.stop()

    # ── Plan tool execution ───────────────────────────────────────────────

    # Tools that may trigger page navigation — we wait for load after these.
    _NAVIGATION_TRIGGERS: frozenset = frozenset({"press_key", "click"})

    # Tools whose effects cannot be confirmed by URL/DOM checks — input field values
    # are not in body.innerText and these tools don't navigate.  Always skip verify.
    _NO_VERIFY_TOOLS: frozenset = frozenset({"fill", "hover", "select_option", "drag_and_drop"})

    def _execute_plan(self, plan: List[dict], history: HistoryManager) -> dict:
        """
        Execute a pre-planned step sequence with per-step verification.

        Returns a result dict:
          {"success": True, "completed_steps": N, "total_steps": N, "message": "...", "current_url": "..."}
        or on failure:
          {"success": False, "completed_steps": N-1, "failed_step": N, "failed_tool": "...",
           "message": "...", "current_url": "..."}

        The caller (plan tool handler in _process_tool_calls) passes this result back to the
        AI so it can take a targeted manual action and re-plan from the current state.
        """
        # All events emitted from inside a plan are tagged {"plan": True} so the
        # frontend can display them as "Plan Step N" instead of "Step N", avoiding
        # numbering collisions with the outer agent loop.
        def _emit_p(event_type: str, data: Any) -> None:
            self._emit(event_type, {**data, "plan": True})

        for step_num, step in enumerate(plan, 1):
            if not self._active:
                return {
                    "success": False, "completed_steps": step_num - 1,
                    "total_steps": len(plan), "message": "Stopped by user.",
                    "current_url": self._browser.current_url(),
                }

            tool             = step.get("tool", "")
            args             = dict(step.get("args", {}))
            verify_condition = step.get("verify", {"type": "none"})
            prev_url         = self._browser.current_url()

            _emit_p("step", {"step": step_num, "status": "thinking"})
            self._flush_human_actions()

            # ── done step inside plan ─────────────────────────────────────
            if tool == "done":
                return {
                    "success": True,
                    "completed_steps": step_num,
                    "total_steps": len(plan),
                    "message": args.get("summary", "Task completed"),
                    "current_url": self._browser.current_url(),
                }

            # ── Resolve heuristic target ──────────────────────────────────
            if "target" in args:
                target   = args.pop("target")
                selector = heuristic_resolve(self._browser.page, target)

                if selector:
                    _emit_p("heuristic", {
                        "step": step_num, "target": target,
                        "selector": selector, "hit": True,
                    })
                    args["selector"] = selector
                else:
                    _emit_p("heuristic", {
                        "step": step_num, "target": target, "hit": False,
                    })
                    return {
                        "success": False,
                        "completed_steps": step_num - 1,
                        "total_steps": len(plan),
                        "failed_step": step_num,
                        "failed_tool": tool,
                        "failed_target": target,
                        "message": (
                            f"Could not automatically locate '{target}' on the page for step {step_num} ({tool}). "
                            f"Take a manual {tool} action targeting the {target.replace('_', ' ')}, "
                            f"then call plan again for the remaining steps."
                        ),
                        "current_url": self._browser.current_url(),
                    }

            # ── Execute the step ──────────────────────────────────────────
            _emit_p("tool_call", {"step": step_num, "tool": tool, "args": args})
            result = run_tool(self._browser.page, tool, args)
            tool_errored = isinstance(result, dict) and "error" in result
            _emit_p("tool_result", {"step": step_num, "tool": tool, "result": result})
            self._emit_screenshot(step=step_num, tool=tool, plan=True)

            # Wait for page to settle BEFORE verifying
            if tool in self._NAVIGATION_TRIGGERS:
                self._wait_for_page()

            self._flush_human_actions()

            # ── Per-step verification (deterministic, zero AI) ────────────
            if tool in self._NO_VERIFY_TOOLS:
                pass

            elif not verify_step(self._browser.page, verify_condition, prev_url=prev_url, on_event=_emit_p):
                if tool_errored:
                    # Tool itself reported an error — hard failure.
                    return {
                        "success": False,
                        "completed_steps": step_num - 1,
                        "total_steps": len(plan),
                        "failed_step": step_num,
                        "failed_tool": tool,
                        "message": (
                            f"Step {step_num} ({tool}) failed: {result.get('error')}. "
                            f"Take a manual action to unblock the page, then call plan again."
                        ),
                        "current_url": self._browser.current_url(),
                    }
                # Tool succeeded but planner's expected state didn't match reality.
                # Soft-warn and continue — the end-of-plan _verify_goal catches real failures.
                logger.debug(
                    f"[runner] Plan step {step_num} ({tool}) verify mismatch — tool succeeded, continuing"
                )
                _emit_p("log", {
                    "message": (
                        f"Plan step {step_num} ({tool}): verify condition did not match "
                        f"but tool succeeded — continuing."
                    ),
                })

        # ── All steps passed — final page settle + goal check ────────────
        self._wait_for_page()
        if not self._verify_goal(on_event=self._emit):
            return {
                "success": False,
                "completed_steps": len(plan),
                "total_steps": len(plan),
                "message": (
                    "All plan steps completed but the goal is not yet fully achieved. "
                    "Review the current page and call plan again or take a manual action."
                ),
                "current_url": self._browser.current_url(),
            }

        return {
            "success": True,
            "completed_steps": len(plan),
            "total_steps": len(plan),
            "message": "All steps completed and goal verified.",
            "current_url": self._browser.current_url(),
        }

    def _wait_for_page(self, timeout: int = 10_000) -> None:
        """
        Wait for the page to reach networkidle after a navigation-triggering
        action (press_key, click).  Timeout is intentionally generous;
        a TimeoutError just means the page is already settled.
        """
        try:
            self._browser.page.wait_for_load_state("networkidle", timeout=timeout)
            logger.debug("[runner] Page settled (networkidle)")
        except Exception:
            # Timeout is fine — page was already idle or navigation didn't happen
            pass

    def _verify_goal(self, on_event=None) -> bool:
        """
        One small AI call (yes/no) to confirm the task was actually achieved.

        Sends only the task description + compact page state (~300 tokens).
        Returns True if the AI says the goal is met, False otherwise.
        """
        state = capture_page_state(self._browser)

        if on_event:
            on_event("verify", {
                "condition": "Goal achieved?",
                "status":    "checking",
                "attempt":   1,
                "total":     1,
                "detail":    f"Asking AI whether '{self._task}' was completed",
            })

        raw = self._llm.complete_text([
            {
                "role": "system",
                "content": (
                    "You verify whether a browser automation task was completed.\n"
                    "Reply with ONLY 'yes' or 'no'."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Task: {self._task}\n\n"
                    f"Current page state:\n{state}\n\n"
                    "Was the task completed successfully?"
                ),
            },
        ])
        self._emit("tokens", self._llm.token_stats())

        achieved = raw.strip().lower().startswith("yes")

        if on_event:
            on_event("verify", {
                "condition": "Goal achieved?",
                "status":    "pass" if achieved else "fail",
                "attempt":   1,
                "total":     1,
                "detail":    f"{'✓ Task completed' if achieved else '✗ Task not yet completed'} — {self._browser.current_url()}",
            })

        return achieved

    # ── Agent loop ────────────────────────────────────────────────────────

    def _run_agent_loop(self, history: HistoryManager) -> None:
        """Main AI-driven loop. AI calls plan() first, recovers manually on failure, re-plans."""
        _last_url:   str           = ""
        _stuck_steps: int          = 0
        _last_tool:  Optional[str] = None

        for step in range(1, self._max_steps + 1):
            if not self._active:
                break

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

            if not self._control.agent_can_act():
                self._emit("log", {"message": "[agent-only locked out — human-only mode]"})
                continue

            finished, _last_tool = self._process_tool_calls(msg.tool_calls, step, history)
            if finished:
                break

            current_url = self._browser.current_url()
            if current_url == _last_url:
                _stuck_steps += 1
            else:
                _stuck_steps = 0
                _last_url    = current_url

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

            # ── Resolve semantic target names the AI uses as selector values ──
            # When the AI writes fill(selector="username_field") or
            # click(selector="submit_button"), we resolve the name to the real
            # CSS selector via the heuristic resolver — zero extra AI calls.
            selector_val = args.get("selector", "")
            if selector_val and selector_val in KNOWN_TARGETS:
                resolved = heuristic_resolve(self._browser.page, selector_val)
                if resolved:
                    self._emit("heuristic", {
                        "step": step, "target": selector_val,
                        "selector": resolved, "hit": True,
                    })
                    args["selector"] = resolved
                else:
                    self._emit("heuristic", {
                        "step": step, "target": selector_val, "hit": False,
                    })
                    # Leave the name in place — some tools accept semantic names
                    # as a fallback; at worst the tool will fail gracefully.

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

            if name == "plan":
                # ── Plan tool: generate → execute → return result to AI ───
                task        = args.get("task", self._task)
                current_url = self._browser.current_url()
                raw_plan    = generate_plan(task, self._llm, current_url=current_url)
                self._emit("tokens", self._llm.token_stats())

                if not raw_plan:
                    plan_result: Dict[str, Any] = {
                        "success": False,
                        "message": (
                            "Could not generate a valid plan. "
                            "Try a more specific task description or take a manual step first."
                        ),
                        "current_url": self._browser.current_url(),
                    }
                else:
                    self._emit("plan", {"steps": len(raw_plan), "mode": "skill"})
                    plan_result = self._execute_plan(raw_plan, history)

                plan_result_str = json.dumps(plan_result)
                history.add_tool_result(tc.id, plan_result_str, tool="plan")
                self._emit("tool_result", {"step": step, "tool": "plan", "result": plan_result})

                if plan_result.get("success"):
                    # Plan fully succeeded — emit done and stop the loop
                    self._emit_screenshot(step=step, tool="done")
                    self._emit("done", {
                        "summary":      plan_result.get("message", "Task completed"),
                        "data":         {},
                        "total_frames": self._recorder.count(),
                    })
                    return True, "plan"

                # Plan failed — AI gets the result and decides how to recover
                last_tool = "plan"
                continue

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

    def _emit_screenshot(self, step: int = 0, tool: str = "", plan: bool = False) -> None:
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
                "plan":         plan,
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
