"""Tool schemas sent to the LLM on every call.

Keeping schemas in a dedicated file makes it easy to audit what the model
can see without wading through dispatch logic.
"""

from typing import Dict, List


TOOL_SCHEMAS: List[Dict] = [
    # ── Navigation ────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate the browser to a URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL including https://"},
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

    # ── Interaction ───────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": (
                "Click an element by interactive-element index (from get_interactive_elements), "
                "CSS selector, or pixel coordinates"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "index":    {"type": "integer", "description": "Element index from get_interactive_elements"},
                    "selector": {"type": "string",  "description": "CSS selector"},
                    "x":        {"type": "integer", "description": "X coordinate"},
                    "y":        {"type": "integer", "description": "Y coordinate"},
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
                    "selector":    {"type": "string",  "description": "CSS selector of the input element"},
                    "text":        {"type": "string",  "description": "Text to type"},
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
                    "key":      {"type": "string", "description": "Key name e.g. 'Enter', 'Tab', 'Escape'"},
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
                    "selector": {"type": "string", "description": "CSS selector"},
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
                    "value":    {"type": "string", "description": "The value attribute of the option"},
                    "label":    {"type": "string", "description": "The visible text label of the option"},
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

    # ── Extraction ────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_page_content",
            "description": (
                "Get the current page URL, title, and visible text. "
                "Prefer find_elements for targeted lookups — this tool returns broad page text."
            ),
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
                    "selector": {"type": "string",  "description": "CSS selector"},
                    "limit":    {"type": "integer", "description": "Max elements to return (default: 20)"},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_interactive_elements",
            "description": (
                "List all interactive elements (links, buttons, inputs) with their index numbers. "
                "Use the returned indices with click(index=N)."
            ),
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
                    "script": {"type": "string", "description": "JavaScript expression to evaluate"},
                },
                "required": ["script"],
            },
        },
    },

    # ── Scroll ────────────────────────────────────────────────────────────────
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
                    "selector": {"type": "string", "description": "CSS selector of the target element"},
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

    # ── Wait ──────────────────────────────────────────────────────────────────
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
            "name": "wait_for_url",
            "description": "Wait for the browser URL to match a pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "url_pattern": {"type": "string", "description": "URL glob or regex pattern to wait for"},
                    "timeout":     {"type": "integer", "description": "Timeout in milliseconds (default: 10000)"},
                },
                "required": ["url_pattern"],
            },
        },
    },

    # ── Control ───────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "done",
            "description": "Mark the task as complete. Call this when the task is fully finished.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Summary of what was accomplished"},
                    "data":    {"type": "object", "description": "Extracted data or results (optional)"},
                },
                "required": ["summary"],
            },
        },
    },
]
