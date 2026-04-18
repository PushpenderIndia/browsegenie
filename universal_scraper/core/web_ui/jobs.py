"""
Scrape job lifecycle: queue-based log capture, job state, and the worker thread.
"""

import csv
import io
import logging
import queue
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .providers import PROVIDERS

# Global registry of active/recent jobs, keyed by job_id.
jobs: Dict[str, "Job"] = {}


# ---------------------------------------------------------------------------
# Logging bridge
# ---------------------------------------------------------------------------

class QueueLogHandler(logging.Handler):
    """
    Logging handler that forwards every log record into a Queue so that
    the SSE endpoint can stream it to the browser in real time.
    """

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self._queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait({
                "type": "log",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": record.levelname,
                "message": record.getMessage(),
            })
        except Exception:
            pass  # never let logging break the scrape


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class Job:
    """Represents a single scrape request and owns its log stream."""

    def __init__(self) -> None:
        self.job_id: str = str(uuid.uuid4())
        self.log_queue: queue.Queue = queue.Queue()
        self.done: threading.Event = threading.Event()
        self.result: Optional[Dict] = None
        self.error: Optional[str] = None

        self._handler = QueueLogHandler(self.log_queue)
        self._handler.setLevel(logging.DEBUG)

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def log(self, level: str, message: str) -> None:
        """Push a manual log entry (not via the logging module)."""
        self.log_queue.put_nowait({
            "type": "log",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        })

    # ------------------------------------------------------------------
    # Logging capture
    # ------------------------------------------------------------------

    def attach(self) -> None:
        """Start capturing all Python log records into this job's queue."""
        logging.getLogger().addHandler(self._handler)

    def detach(self) -> None:
        """Stop capturing log records."""
        logging.getLogger().removeHandler(self._handler)


# ---------------------------------------------------------------------------
# Scrape worker
# ---------------------------------------------------------------------------

def run_job(
    job: Job,
    url: str,
    provider: str,
    model: str,
    api_key: str,
    fields: List[str],
    fmt: str,
) -> None:
    """
    Execute a scrape in a background thread.

    Attaches a log handler so all internal scraper logs flow into the
    job's queue, then signals completion via ``job.done``.
    """
    job.attach()
    try:
        provider_name = PROVIDERS.get(provider, {}).get("name", provider)
        job.log("INFO", f"Provider: {provider_name} | Model: {model}")

        # Import here to avoid circular imports at module load time.
        from universal_scraper import UniversalScraper

        scraper = UniversalScraper(api_key=api_key or None, model_name=model)
        if fields:
            scraper.set_fields(fields)

        job.log("INFO", f"Fields: {', '.join(scraper.get_fields())}")
        job.log("INFO", f"Fetching: {url}")

        result = scraper.scrape_url(url, save_to_file=False, format=fmt)

        # When CSV is requested, generate the CSV string from the data
        # so the UI can display a table and download a proper .csv file.
        if fmt == "csv":
            result["csv_content"] = _to_csv(result.get("data", []))

        # Attach token usage summary from the extractor.
        result["token_usage"] = scraper.extractor.get_token_usage()

        job.result = result
        items = result.get("metadata", {}).get("items_extracted", 0)
        job.log("INFO", f"Done — {items} item(s) extracted")

    except Exception as exc:
        job.error = str(exc)
        job.log("ERROR", f"Failed: {exc}")

    finally:
        job.detach()
        job.log_queue.put_nowait({"type": "done"})
        job.done.set()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_csv(data) -> str:
    """Convert a list of dicts (or a single dict) to a CSV string."""
    if isinstance(data, dict):
        data = [data]
    if not data:
        return ""

    buf = io.StringIO()
    fieldnames = sorted({k for row in data if isinstance(row, dict) for k in row})
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in data:
        if isinstance(row, dict):
            writer.writerow(row)
    return buf.getvalue()
