"""Tool dispatch: routes tool-call names to their handler functions."""

from typing import Any, Dict

from playwright.sync_api import Page

from .navigation  import navigate, go_back, go_forward, reload
from .interaction import click, fill, press_key, hover, select_option, drag_and_drop
from .extraction  import get_page_content, find_elements, get_interactive_elements, execute_js
from .scroll      import scroll, scroll_to_element, scroll_to_bottom, scroll_to_top
from .wait        import wait_for_element, wait_for_load, wait_for_url

# Re-export so callers can do: from .registry import schemas_for, run_tool
from .phases import schemas_for  # noqa: F401

_DISPATCH: Dict[str, Any] = {
    "navigate":                 lambda page, a: navigate(page, **a),
    "go_back":                  lambda page, _: go_back(page),
    "go_forward":               lambda page, _: go_forward(page),
    "reload":                   lambda page, _: reload(page),
    "click":                    lambda page, a: click(page, **a),
    "fill":                     lambda page, a: fill(page, **a),
    "press_key":                lambda page, a: press_key(page, **a),
    "hover":                    lambda page, a: hover(page, **a),
    "select_option":            lambda page, a: select_option(page, **a),
    "drag_and_drop":            lambda page, a: drag_and_drop(page, **a),
    "get_page_content":         lambda page, _: get_page_content(page),
    "find_elements":            lambda page, a: find_elements(page, **a),
    "get_interactive_elements": lambda page, _: get_interactive_elements(page),
    "execute_js":               lambda page, a: execute_js(page, **a),
    "scroll":                   lambda page, a: scroll(page, **a),
    "scroll_to_element":        lambda page, a: scroll_to_element(page, **a),
    "scroll_to_bottom":         lambda page, _: scroll_to_bottom(page),
    "scroll_to_top":            lambda page, _: scroll_to_top(page),
    "wait_for_element":         lambda page, a: wait_for_element(page, **a),
    "wait_for_load":            lambda page, a: wait_for_load(page, **a),
    "wait_for_url":             lambda page, a: wait_for_url(page, **a),
    # "done" is handled as a special case in the agent loop, not dispatched here.
}


def run_tool(page: Page, name: str, args: Dict[str, Any]) -> Dict:
    """Execute *name* with *args* on *page*. Returns the tool result dict."""
    handler = _DISPATCH.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(page, args)
    except Exception as exc:
        return {"error": str(exc), "tool": name}
