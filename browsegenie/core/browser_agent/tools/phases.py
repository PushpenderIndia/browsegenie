"""Phase-based tool selection.

Sends only the tools relevant to the predicted next phase instead of all 22+,
saving ~620-720 tokens per step on typical browse tasks.

Phase flow:
    navigate → read → interact → read → ...
                              ↘ wait → read → ...
"""

from typing import Dict, List, Optional

from .schemas import (
    NAVIGATE, GO_BACK, GO_FORWARD, RELOAD,
    CLICK, FILL, PRESS_KEY, HOVER, SELECT_OPTION, DRAG_AND_DROP,
    GET_PAGE_CONTENT, FIND_ELEMENTS, GET_INTERACTIVE_ELEMENTS, EXECUTE_JS,
    SCROLL, SCROLL_TO_ELEMENT, SCROLL_TO_BOTTOM, SCROLL_TO_TOP,
    WAIT_FOR_ELEMENT, WAIT_FOR_LOAD, WAIT_FOR_URL,
    DONE,
)

# Each phase always includes DONE so the agent can terminate at any point.
PHASE_SCHEMAS: Dict[str, List] = {
    "navigate": [NAVIGATE, GO_BACK, GO_FORWARD, RELOAD, DONE],
    "read":     [GET_PAGE_CONTENT, FIND_ELEMENTS, GET_INTERACTIVE_ELEMENTS, EXECUTE_JS,
                 SCROLL, SCROLL_TO_ELEMENT, SCROLL_TO_BOTTOM, SCROLL_TO_TOP, DONE],
    "interact": [CLICK, FILL, PRESS_KEY, HOVER, SELECT_OPTION, DRAG_AND_DROP, NAVIGATE, DONE],
    "wait":     [WAIT_FOR_ELEMENT, WAIT_FOR_LOAD, WAIT_FOR_URL, DONE],
}

# Maps the last tool called → the phase most likely needed next.
_NEXT_PHASE: Dict[str, str] = {
    # Navigation lands on a new page → read it.
    "navigate":    "read",
    "go_back":     "read",
    "go_forward":  "read",
    "reload":      "read",
    # Reading reveals elements → interact with them.
    "get_page_content":         "interact",
    "find_elements":            "interact",
    "get_interactive_elements": "interact",
    # JS result may change page → re-read.
    "execute_js": "read",
    # Scrolling reveals more content → keep reading.
    "scroll":            "read",
    "scroll_to_element": "read",
    "scroll_to_bottom":  "read",
    "scroll_to_top":     "read",
    # After a click the page may change → read the result.
    "click":        "read",
    # After fill the next step is usually submit → stay in interact.
    "fill":         "interact",
    # Key press submits / confirms → read result.
    "press_key":    "read",
    # Hover reveals a menu → interact with it.
    "hover":        "interact",
    # Dropdown selected → interact to submit.
    "select_option": "interact",
    # Drag result needs inspection → read.
    "drag_and_drop": "read",
    # Wait finished → read what changed.
    "wait_for_element": "read",
    "wait_for_load":    "read",
    "wait_for_url":     "read",
}


def schemas_for(last_tool: Optional[str] = None) -> List:
    """Return tool schemas for the phase that follows *last_tool*.

    Defaults to the ``navigate`` phase at task start (``last_tool=None``).
    Unknown tools fall back to ``read``.
    """
    phase = _NEXT_PHASE.get(last_tool, "read") if last_tool else "navigate"
    return PHASE_SCHEMAS[phase]
