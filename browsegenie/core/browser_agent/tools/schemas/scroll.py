"""Scroll tool schemas."""

SCROLL = {
    "type": "function",
    "function": {
        "name": "scroll",
        "description": "Scroll direction",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["down", "up", "left", "right"]},
                "pixels":    {"type": "integer"},
            },
        },
    },
}

SCROLL_TO_ELEMENT = {
    "type": "function",
    "function": {
        "name": "scroll_to_element",
        "description": "Scroll to selector",
        "parameters": {
            "type": "object",
            "properties": {"selector": {"type": "string"}},
            "required": ["selector"],
        },
    },
}

SCROLL_TO_BOTTOM = {
    "type": "function",
    "function": {"name": "scroll_to_bottom", "description": "Scroll bottom", "parameters": {"type": "object", "properties": {}}},
}

SCROLL_TO_TOP = {
    "type": "function",
    "function": {"name": "scroll_to_top", "description": "Scroll top", "parameters": {"type": "object", "properties": {}}},
}

SCHEMAS = [SCROLL, SCROLL_TO_ELEMENT, SCROLL_TO_BOTTOM, SCROLL_TO_TOP]
