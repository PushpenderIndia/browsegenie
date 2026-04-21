"""Navigation tool schemas."""

NAVIGATE = {
    "type": "function",
    "function": {
        "name": "navigate",
        "description": "Open URL",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
}

GO_BACK = {
    "type": "function",
    "function": {"name": "go_back", "description": "Back", "parameters": {"type": "object", "properties": {}}},
}

GO_FORWARD = {
    "type": "function",
    "function": {"name": "go_forward", "description": "Forward", "parameters": {"type": "object", "properties": {}}},
}

RELOAD = {
    "type": "function",
    "function": {"name": "reload", "description": "Reload page", "parameters": {"type": "object", "properties": {}}},
}

SCHEMAS = [NAVIGATE, GO_BACK, GO_FORWARD, RELOAD]
