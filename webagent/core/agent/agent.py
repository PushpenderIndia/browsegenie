"""
AI Agent orchestrator.

Creates a plan from a natural-language requirement and streams step
updates so the frontend can render an animated todo list.

Usage (from server route):
    task = start_plan(requirement, provider, model, api_key)
    # then stream from agent_tasks[task.task_id].log_queue
"""

import logging
import queue
import threading
import uuid
from typing import Any, Dict, List, Optional

from .requirement_parser import parse_requirement
from .url_finder import find_urls

logger = logging.getLogger(__name__)

# Global registry: task_id → AgentTask
agent_tasks: Dict[str, "AgentTask"] = {}


# ---------------------------------------------------------------------------
# AgentTask
# ---------------------------------------------------------------------------

class AgentTask:
    """Holds the state and event queue for a single agent planning run."""

    def __init__(self) -> None:
        self.task_id: str = str(uuid.uuid4())
        self.log_queue: queue.Queue = queue.Queue()
        self.done: threading.Event = threading.Event()
        self.result: Optional[Dict] = None
        self.error: Optional[str] = None

    # ── helpers ──────────────────────────────────────────────────────────

    def push(self, event: Dict) -> None:
        self.log_queue.put_nowait(event)

    def step_update(
        self,
        step_id: str,
        status: str,          # pending | running | done | error
        title: str,
        detail: str = "",
        data: Any = None,
    ) -> None:
        event: Dict[str, Any] = {
            "type":    "step_update",
            "step_id": step_id,
            "status":  status,
            "title":   title,
            "detail":  detail,
        }
        if data is not None:
            event["data"] = data
        self.push(event)


# ---------------------------------------------------------------------------
# Plan worker
# ---------------------------------------------------------------------------

_STEPS_DEFINITION = [
    {"id": "parse",     "title": "Parse requirement",  "status": "pending"},
    {"id": "find_urls", "title": "Find target URLs",    "status": "pending"},
    {"id": "fill",      "title": "Auto-fill form",      "status": "pending"},
]


def _create_plan(
    task: AgentTask,
    requirement: str,
    provider: str,
    model: str,
    api_key: str,
) -> None:
    """Background worker: parse → find URLs → signal ready."""
    try:
        # Announce the step structure
        task.push({"type": "steps_init", "steps": _STEPS_DEFINITION})

        # ── Step 1: Parse requirement ───────────────────────────────────
        task.step_update("parse", "running", "Parsing your requirement…")
        parsed = parse_requirement(requirement, api_key, model, provider)

        query  = parsed.get("query", "")
        sites  = parsed.get("sites", [])
        fields = parsed.get("fields", [])

        task.step_update(
            "parse", "done",
            "Requirement parsed",
            f'Query: "{query}" · Sites: {", ".join(sites)}',
            data=parsed,
        )

        # ── Step 2: Find URLs ───────────────────────────────────────────
        task.step_update("find_urls", "running", "Searching for target URLs…")

        if not sites:
            raise ValueError("Could not detect any target sites in the requirement.")

        url_results: List[Dict] = find_urls(sites, query)
        urls = [r["url"] for r in url_results]

        detail = "  ·  ".join(f"{r['site']} → {r['url']}" for r in url_results)
        task.step_update(
            "find_urls", "done",
            f"Found {len(urls)} URL(s)",
            detail,
            data=url_results,
        )

        # ── Step 3: Fill form ───────────────────────────────────────────
        task.step_update("fill", "running", "Auto-filling form…")

        task.result = {
            "urls":        urls,
            "fields":      fields,
            "query":       query,
            "sites":       sites,
            "url_details": url_results,
        }

        task.step_update(
            "fill", "done",
            "Form ready — review and execute",
            f'{len(urls)} URL(s), {len(fields)} field(s)',
        )

        task.push({
            "type":        "plan_ready",
            "urls":        urls,
            "fields":      fields,
            "url_details": url_results,
        })

    except Exception as exc:
        task.error = str(exc)
        task.push({"type": "error", "message": str(exc)})
        logger.error(f"[agent] Task {task.task_id} failed: {exc}")

    finally:
        task.push({"type": "done"})
        task.done.set()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_plan(
    requirement: str,
    provider: str,
    model: str,
    api_key: str,
) -> AgentTask:
    """Kick off planning in a daemon thread; return the AgentTask immediately."""
    task = AgentTask()
    agent_tasks[task.task_id] = task

    threading.Thread(
        target=_create_plan,
        args=(task, requirement, provider, model, api_key),
        daemon=True,
    ).start()

    return task
