"""Control tool schemas."""

PLAN = {
    "type": "function",
    "function": {
        "name": "plan",
        "description": (
            "Generate and execute a step-by-step browser plan for a task. "
            "Always call this FIRST before any other action. "
            "Executes each step with heuristic element resolution and per-step verification. "
            "On success, the task is complete — call done. "
            "On failure, the result explains which step failed and the current page state, "
            "so you can take one targeted manual action to unblock, then call plan again."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "What to accomplish from the current page state.",
                },
            },
            "required": ["task"],
        },
    },
}

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

SCHEMAS = [PLAN, DONE]
