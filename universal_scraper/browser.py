"""
Browser Agent convenience function for running browser automation tasks.
"""

import queue as _queue
import time as _time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .core.browser_agent.agent.sessions import create_session


def browse(
    task: str,
    api_key: str,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    headless: bool = True,
    on_event: Optional[Callable[[str, Dict], None]] = None,
    timeout: Optional[float] = None,
    show_logs: bool = True,
) -> Dict[str, Any]:
    """
    Run a browser automation task and return the result.

    Args:
        task: Natural language description of what to do in the browser
        api_key: AI provider API key (Gemini, OpenAI, Anthropic, etc.)
        model_name: AI model name. Defaults to 'gemini-2.5-flash'.
                    Examples: 'gpt-4o', 'claude-3-5-sonnet-20241022',
                    'gemini-2.5-flash'
        provider: Provider name - 'google', 'openai', 'anthropic', 'ollama',
                  'deepseek', 'mistral', 'xai', 'cohere'.
                  Auto-detected from model_name if not specified.
        headless: Run browser in headless mode (default True). Set False to
                  watch the browser in action.
        on_event: Optional callback for real-time streaming events.
                  Called as on_event(event_type, event_data) for each event.
                  Event types: 'start', 'step', 'tool_call', 'tool_result',
                  'screenshot', 'tokens', 'log', 'done', 'error'
        timeout: Maximum seconds to wait for the task to complete.
                 Default is None (wait indefinitely).
        show_logs: Print real-time progress logs to stdout (default True).
                   Set to False to run silently.

    Returns:
        Dict with keys:
            summary     - Text summary produced by the agent when done
            data        - Structured data extracted by the agent (if any)
            screenshots - List of screenshot frame dicts captured during run
            steps       - Number of steps the agent took
            success     - True if the task completed successfully
            error       - Error message string if success is False, else None

    Examples::

        from universal_scraper import browse

        # Basic task with Gemini (default) - logs printed automatically
        result = browse(
            task="Go to wikipedia.org and find the featured article title",
            api_key="your_gemini_api_key",
        )
        print(result["summary"])
        print(result["data"])

        # Silent mode
        result = browse(
            task="Go to wikipedia.org and find the featured article title",
            api_key="your_gemini_api_key",
            show_logs=False,
        )

        # With OpenAI
        result = browse(
            task="Search for 'Python' on PyPI and return the latest version",
            api_key="your_openai_api_key",
            model_name="gpt-4o",
        )

        # With Anthropic Claude
        result = browse(
            task="Go to news.ycombinator.com and list the top 5 story titles",
            api_key="your_anthropic_api_key",
            model_name="claude-3-5-sonnet-20241022",
        )

        # Custom event handler (receives events in addition to default logs)
        def on_event(event_type, data):
            if event_type == "screenshot":
                save_screenshot(data["image"])

        result = browse(
            task="Find the price of the first product on example.com/shop",
            api_key="your_gemini_api_key",
            on_event=on_event,
        )

        # Visible browser + timeout
        result = browse(
            task="Log in to example.com with user@test.com / pass123",
            api_key="your_gemini_api_key",
            headless=False,
            timeout=120,
        )
    """
    resolved_model, resolved_provider = _resolve_model_and_provider(
        model_name, provider
    )

    if show_logs:
        print(f"[browse] Task: {task}")
        print(f"[browse] Model: {resolved_model} ({resolved_provider})")
        print(f"[browse] Starting browser agent...")

    session = create_session(
        task=task,
        model=resolved_model,
        provider=resolved_provider,
        api_key=api_key,
        headless=headless,
    )

    result: Dict[str, Any] = {
        "summary": "",
        "data": {},
        "screenshots": [],
        "steps": 0,
        "success": False,
        "error": None,
    }

    try:
        deadline = _time.monotonic() + timeout if timeout is not None else None

        while True:
            # Compute remaining time for this queue.get call
            wait = 1.0
            if deadline is not None:
                remaining = deadline - _time.monotonic()
                if remaining <= 0:
                    session.stop()
                    result["error"] = "Task timed out"
                    if show_logs:
                        print("[browse] Timed out.")
                    break
                wait = min(remaining, 1.0)

            try:
                event = session.event_queue.get(timeout=wait)
                event_type = event["type"]
                event_data = event["data"]
            except _queue.Empty:
                if session.is_done:
                    break
                continue

            if on_event is not None:
                on_event(event_type, event_data)

            if show_logs:
                _log_event(event_type, event_data)

            if event_type == "step":
                result["steps"] = event_data.get("step", result["steps"])
            elif event_type == "done":
                result["summary"] = event_data.get("summary", "")
                result["data"] = event_data.get("data", {})
                result["success"] = True
                break
            elif event_type == "error":
                result["error"] = event_data.get("message", "Unknown error")
                break

    finally:
        result["screenshots"] = session.get_playback_frames()
        if show_logs:
            frames = len(result["screenshots"])
            status = "completed" if result["success"] else f"failed: {result['error']}"
            print(f"[browse] {status} | steps={result['steps']} screenshots={frames}")

    return result


def _log_event(event_type: str, data: Dict) -> None:
    """Print a human-readable log line for a browser agent event."""
    if event_type == "start":
        print(f"[browse] Agent started")
    elif event_type == "step":
        step = data.get("step", "?")
        print(f"[browse] Step {step}: thinking...")
    elif event_type == "tool_call":
        tool = data.get("tool", "?")
        args = data.get("args", {})
        # Format args compactly: show only values, truncate long strings
        arg_str = ", ".join(
            f"{k}={repr(v)[:60]}" for k, v in args.items()
        ) if args else ""
        print(f"[browse]   -> {tool}({arg_str})")
    elif event_type == "tool_result":
        tool = data.get("tool", "?")
        result = data.get("result", {})
        # Show a brief snippet of the result
        snippet = str(result)[:120].replace("\n", " ")
        print(f"[browse]      {tool} result: {snippet}")
    elif event_type == "log":
        msg = data.get("message", "")
        print(f"[browse] {msg}")
    elif event_type == "tokens":
        total = data.get("total_tokens", 0)
        calls = data.get("api_calls", 0)
        print(f"[browse] Tokens used: {total} ({calls} API calls)")
    elif event_type == "done":
        summary = data.get("summary", "")
        print(f"[browse] Done: {summary[:200]}")
    elif event_type == "error":
        msg = data.get("message", "Unknown error")
        print(f"[browse] Error: {msg}")


def _resolve_model_and_provider(
    model_name: Optional[str],
    provider: Optional[str],
) -> Tuple[str, str]:
    """Return (model, provider), auto-detecting provider from model name."""
    if model_name is None:
        model_name = "gemini-2.5-flash"

    if provider:
        return model_name, provider

    lower = model_name.lower()

    if lower.startswith("gpt-") or lower.startswith("o1") or lower.startswith("o3") or lower.startswith("o4"):
        return model_name, "openai"
    if lower.startswith("claude-"):
        return model_name, "anthropic"
    if lower.startswith("gemini-"):
        return model_name, "google"
    if lower.startswith("mistral"):
        return model_name, "mistral"
    if lower.startswith("deepseek"):
        return model_name, "deepseek"
    if lower.startswith("ollama/"):
        return model_name, "ollama"
    if lower.startswith("command"):
        return model_name, "cohere"
    if lower.startswith("grok"):
        return model_name, "xai"

    # Default to Google/Gemini
    return model_name, "google"
