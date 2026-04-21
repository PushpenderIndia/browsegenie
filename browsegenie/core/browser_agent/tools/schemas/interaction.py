"""Interaction tool schemas."""

CLICK = {
    "type": "function",
    "function": {
        "name": "click",
        "description": "Click element (index | selector | x,y)",
        "parameters": {
            "type": "object",
            "properties": {
                "index":    {"type": "integer"},
                "selector": {"type": "string"},
                "x":        {"type": "integer"},
                "y":        {"type": "integer"},
            },
        },
    },
}

FILL = {
    "type": "function",
    "function": {
        "name": "fill",
        "description": "Type text (index | selector)",
        "parameters": {
            "type": "object",
            "properties": {
                "text":        {"type": "string"},
                "index":       {"type": "integer"},
                "selector":    {"type": "string"},
                "clear_first": {"type": "boolean"},
            },
            "required": ["text"],
        },
    },
}

PRESS_KEY = {
    "type": "function",
    "function": {
        "name": "press_key",
        "description": "Press key",
        "parameters": {
            "type": "object",
            "properties": {
                "key":      {"type": "string"},
                "selector": {"type": "string"},
            },
            "required": ["key"],
        },
    },
}

HOVER = {
    "type": "function",
    "function": {
        "name": "hover",
        "description": "Hover element",
        "parameters": {
            "type": "object",
            "properties": {"selector": {"type": "string"}},
            "required": ["selector"],
        },
    },
}

SELECT_OPTION = {
    "type": "function",
    "function": {
        "name": "select_option",
        "description": "Select dropdown option",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "value":    {"type": "string"},
                "label":    {"type": "string"},
            },
            "required": ["selector"],
        },
    },
}

DRAG_AND_DROP = {
    "type": "function",
    "function": {
        "name": "drag_and_drop",
        "description": "Drag source → target",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "target": {"type": "string"},
            },
            "required": ["source", "target"],
        },
    },
}

SCHEMAS = [CLICK, FILL, PRESS_KEY, HOVER, SELECT_OPTION, DRAG_AND_DROP]
