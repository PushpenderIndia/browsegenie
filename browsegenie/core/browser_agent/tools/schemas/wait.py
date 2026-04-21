"""Wait tool schemas."""

WAIT_FOR_ELEMENT = {
    "type": "function",
    "function": {
        "name": "wait_for_element",
        "description": "Wait for element state",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "state":    {"type": "string", "enum": ["visible", "hidden", "attached", "detached"]},
                "timeout":  {"type": "integer"},
            },
            "required": ["selector"],
        },
    },
}

WAIT_FOR_LOAD = {
    "type": "function",
    "function": {
        "name": "wait_for_load",
        "description": "Wait for load state",
        "parameters": {
            "type": "object",
            "properties": {
                "state":   {"type": "string", "enum": ["load", "domcontentloaded", "networkidle"]},
                "timeout": {"type": "integer"},
            },
        },
    },
}

WAIT_FOR_URL = {
    "type": "function",
    "function": {
        "name": "wait_for_url",
        "description": "Wait for URL match",
        "parameters": {
            "type": "object",
            "properties": {
                "url_pattern": {"type": "string"},
                "timeout":     {"type": "integer"},
            },
            "required": ["url_pattern"],
        },
    },
}

SCHEMAS = [WAIT_FOR_ELEMENT, WAIT_FOR_LOAD, WAIT_FOR_URL]
