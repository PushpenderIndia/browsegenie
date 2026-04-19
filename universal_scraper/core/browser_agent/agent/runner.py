import json
import queue
from typing import Any, Dict, List, Optional

import litellm

from ..browser.session import BrowserSession
from ..playback.recorder import ScreenshotRecorder
from ..tools.registry import get_schemas, run_tool


_PROVIDER_PREFIXES = {
    "google":   "gemini/",
    "ollama":   "ollama/",
    "deepseek": "deepseek/",
    "mistral":  "mistral/",
    "cohere":   "cohere/",
    "xai":      "xai/",
}

_SYSTEM_PROMPT = (
    "You are a browser automation agent. Complete the given task using the provided tools.\n"
    "After each action you receive the updated page state: URL, interactive elements, and visible text.\n"
    "Use get_interactive_elements to discover clickable items by index before using click(index=...).\n"
    "When the task is fully finished, call the done tool with a clear summary and any extracted data."
)


def _normalize_model(provider: str, model: str) -> str:
    prefix = _PROVIDER_PREFIXES.get(provider, "")
    if prefix and not model.startswith(prefix):
        return prefix + model
    return model


def _capture_page_state(browser: BrowserSession) -> str:
    page = browser.page
    try:
        url = page.url
        title = page.title()
        body = page.query_selector("body")
        text = (body.inner_text() if body else "")[:4000]
        elements = page.evaluate("""
            () => {
                const sel = 'a[href], button, input, select, textarea, [onclick], [role="button"]';
                return Array.from(document.querySelectorAll(sel)).slice(0, 40).map((el, i) => ({
                    index: i,
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || el.value || el.placeholder || '').slice(0, 80).trim(),
                    href: el.href || null,
                    type: el.type || null,
                }));
            }
        """)
        return (
            f"URL: {url}\n"
            f"Title: {title}\n\n"
            f"Interactive elements:\n{json.dumps(elements, indent=2)}\n\n"
            f"Visible text (first 4000 chars):\n{text}"
        )
    except Exception as e:
        return f"URL: {browser.current_url()}\n[Could not read page state: {e}]"


class BrowserAgent:
    def __init__(
        self,
        task: str,
        model: str,
        provider: str = "",
        api_key: Optional[str] = None,
        headless: bool = True,
        max_steps: int = 50,
    ):
        self._task = task
        self._model = _normalize_model(provider, model)
        self._api_key = api_key
        self._max_steps = max_steps
        self._browser = BrowserSession(headless=headless)
        self._queue: queue.Queue = queue.Queue()
        self._recorder = ScreenshotRecorder()
        self._active = False
        self._cumulative_tokens: Dict[str, Any] = {
            "total_tokens":            0,
            "total_prompt_tokens":     0,
            "total_completion_tokens": 0,
            "cache_hits":              0,
            "api_calls":               0,
            "calls":                   [],
        }

    def _emit(self, event_type: str, data: Any) -> None:
        self._queue.put_nowait({"type": event_type, "data": data})

    def _emit_screenshot(self, step: int = 0, tool: str = "") -> None:
        try:
            image = self._browser.screenshot_jpeg_b64()
            url = self._browser.current_url()
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

    def _call_llm(self, messages: List[Dict]) -> Any:
        kwargs: Dict[str, Any] = {
            "model":       self._model,
            "messages":    messages,
            "tools":       get_schemas(),
            "tool_choice": "auto",
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        response = litellm.completion(**kwargs)
        self._accumulate_tokens(response)
        return response

    def _accumulate_tokens(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if not usage:
            return
        prompt     = int(getattr(usage, "prompt_tokens",     0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        total      = int(getattr(usage, "total_tokens",      0) or 0)

        ct = self._cumulative_tokens
        ct["total_prompt_tokens"]     += prompt
        ct["total_completion_tokens"] += completion
        ct["total_tokens"]            += total
        ct["api_calls"]               += 1
        ct["calls"].append({
            "model":             self._model,
            "prompt_tokens":     prompt,
            "completion_tokens": completion,
            "total_tokens":      total,
            "from_cache":        False,
        })
        self._emit("tokens", dict(ct))

    def run(self) -> None:
        self._active = True
        self._browser.start()
        messages: List[Dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Task: {self._task}\n\nInitial state:\n{_capture_page_state(self._browser)}",
            },
        ]
        try:
            self._emit("start", {"task": self._task})
            self._emit_screenshot(step=0, tool="")

            for step in range(1, self._max_steps + 1):
                if not self._active:
                    break

                self._emit("step", {"step": step, "status": "thinking"})

                response = self._call_llm(messages)
                msg = response.choices[0].message

                msg_dict: Dict[str, Any] = {"role": "assistant"}
                if msg.content:
                    msg_dict["content"] = msg.content
                if msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                else:
                    msg_dict.setdefault("content", "")
                messages.append(msg_dict)

                if not msg.tool_calls:
                    if msg.content:
                        self._emit("log", {"message": msg.content})
                    break

                finished = False
                for tc in msg.tool_calls:
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
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": '{"status":"completed"}',
                        })
                        finished = True
                        break

                    result = run_tool(self._browser.page, name, args)
                    self._emit("tool_result", {"step": step, "tool": name, "result": result})
                    self._emit_screenshot(step=step, tool=name)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    })

                if finished:
                    break

                messages.append({
                    "role": "user",
                    "content": f"Continuing. Current state:\n{_capture_page_state(self._browser)}",
                })
            else:
                self._emit_screenshot(step=self._max_steps, tool="done")
                self._emit("done", {
                    "summary": "Maximum steps reached without completion.",
                    "data": {},
                    "total_frames": self._recorder.count(),
                })

        except Exception as e:
            self._emit("error", {"message": str(e)})
        finally:
            self._active = False
            self._browser.stop()

    @property
    def event_queue(self) -> queue.Queue:
        return self._queue

    @property
    def recorder(self) -> ScreenshotRecorder:
        return self._recorder

    def stop(self) -> None:
        self._active = False
        self._browser.stop()
