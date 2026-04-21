"""Control tool schemas."""

DONE = {
    "type": "function",
    "function": {
        "name": "done",
        "description": "Finish task",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "data":    {"type": "object"},
            },
            "required": ["summary"],
        },
    },
}

SCHEMAS = [DONE]
