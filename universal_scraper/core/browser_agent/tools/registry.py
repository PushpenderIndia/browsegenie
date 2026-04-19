from typing import Any, Dict, List
from playwright.sync_api import Page

from .navigation import navigate, go_back, go_forward, reload
from .interaction import click, fill, press_key, hover, select_option, drag_and_drop
from .extraction import get_page_content, find_elements, get_interactive_elements, execute_js
from .scroll import scroll, scroll_to_element, scroll_to_bottom, scroll_to_top
from .wait import wait_for_element, wait_for_load, wait_for_url


TOOL_SCHEMAS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate the browser to a URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL including https://"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "go_back",
            "description": "Navigate back in browser history",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "go_forward",
            "description": "Navigate forward in browser history",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reload",
            "description": "Reload the current page",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click an element by CSS selector, interactive element index (from get_interactive_elements), or pixel coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector"},
                    "index": {"type": "integer", "description": "Element index from get_interactive_elements"},
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fill",
            "description": "Type text into an input field or textarea",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the input element"},
                    "text": {"type": "string", "description": "Text to type"},
                    "clear_first": {"type": "boolean", "description": "Clear existing text first (default: true)"},
                },
                "required": ["selector", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a keyboard key (Enter, Tab, Escape, ArrowDown, ArrowUp, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name e.g. 'Enter', 'Tab', 'Escape', 'ArrowDown'"},
                    "selector": {"type": "string", "description": "Focus this element first (optional)"},
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hover",
            "description": "Move the mouse over an element",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector"}
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "select_option",
            "description": "Select an option from a <select> dropdown element",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the <select> element"},
                    "value": {"type": "string", "description": "The value attribute of the option"},
                    "label": {"type": "string", "description": "The visible text label of the option"},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drag_and_drop",
            "description": "Drag an element and drop it onto another element",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "CSS selector of the element to drag"},
                    "target": {"type": "string", "description": "CSS selector of the drop target"},
                },
                "required": ["source", "target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_content",
            "description": "Get the current page URL, title, visible text content, and HTML snippet",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_elements",
            "description": "Find DOM elements matching a CSS selector and return their properties",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector"},
                    "limit": {"type": "integer", "description": "Max elements to return (default: 20)"},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_interactive_elements",
            "description": "List all interactive elements (links, buttons, inputs) with their index numbers for use with click(index=...)",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_js",
            "description": "Evaluate a JavaScript expression in the browser and return the result",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "JavaScript expression to evaluate"}
                },
                "required": ["script"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll the page in a direction",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["down", "up", "left", "right"],
                        "description": "Scroll direction",
                    },
                    "pixels": {"type": "integer", "description": "Pixels to scroll (default: 500)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_to_element",
            "description": "Scroll until a specific element is in view",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the target element"}
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_to_bottom",
            "description": "Scroll to the very bottom of the page",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_to_top",
            "description": "Scroll to the very top of the page",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_element",
            "description": "Wait for an element to reach a specific state on the page",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector"},
                    "state": {
                        "type": "string",
                        "enum": ["visible", "hidden", "attached", "detached"],
                        "description": "State to wait for (default: visible)",
                    },
                    "timeout": {"type": "integer", "description": "Timeout in milliseconds (default: 10000)"},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_load",
            "description": "Wait for the page to finish loading",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "enum": ["load", "domcontentloaded", "networkidle"],
                        "description": "Load state to wait for (default: domcontentloaded)",
                    },
                    "timeout": {"type": "integer", "description": "Timeout in milliseconds (default: 10000)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "done",
            "description": "Mark the task as complete. Call this when the task is fully finished.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Summary of what was accomplished"},
                    "data": {"type": "object", "description": "Extracted data or results (optional)"},
                },
                "required": ["summary"],
            },
        },
    },
]

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
}


def get_schemas() -> List[Dict]:
    return TOOL_SCHEMAS


def run_tool(page: Page, name: str, args: Dict[str, Any]) -> Dict:
    handler = _DISPATCH.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(page, args)
    except Exception as e:
        return {"error": str(e), "tool": name}
