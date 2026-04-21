"""Extraction tool schemas."""

GET_PAGE_CONTENT = {
    "type": "function",
    "function": {
        "name": "get_page_content",
        "description": "Page URL, title, text",
        "parameters": {"type": "object", "properties": {}},
    },
}

FIND_ELEMENTS = {
    "type": "function",
    "function": {
        "name": "find_elements",
        "description": "Query DOM elements",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "limit":    {"type": "integer"},
            },
            "required": ["selector"],
        },
    },
}

GET_INTERACTIVE_ELEMENTS = {
    "type": "function",
    "function": {
        "name": "get_interactive_elements",
        "description": "List clickable elements with index",
        "parameters": {"type": "object", "properties": {}},
    },
}

EXECUTE_JS = {
    "type": "function",
    "function": {
        "name": "execute_js",
        "description": "Run JS",
        "parameters": {
            "type": "object",
            "properties": {"script": {"type": "string"}},
            "required": ["script"],
        },
    },
}

SCHEMAS = [GET_PAGE_CONTENT, FIND_ELEMENTS, GET_INTERACTIVE_ELEMENTS, EXECUTE_JS]
