"""
Flask application factory and API route definitions.
"""

import json
import logging
import os
import queue
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, stream_with_context

from .jobs import Job, jobs, run_job
from .providers import PROVIDERS, get_models

# Path to the HTML template that is served for every GET /
_TEMPLATE_PATH = Path(__file__).parent / "template.html"


def _load_template() -> str:
    """Read the UI template from disk once at startup."""
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.logger.setLevel(logging.WARNING)

    _html = _load_template()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return _html

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    @app.route("/api/providers")
    def api_providers():
        """Return provider metadata (name, key hint, docs link, saved env key)."""
        payload = {
            key: {
                "name":       cfg["name"],
                "placeholder": cfg["placeholder"],
                "docs_url":   cfg["docs_url"],
                "saved_key":  os.getenv(cfg["env_var"] or "", ""),
            }
            for key, cfg in PROVIDERS.items()
        }
        return jsonify(payload)

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    @app.route("/api/models")
    def api_models():
        """
        Return the model list for a provider.

        Query params:
          provider  — one of google | openai | anthropic | ollama
          api_key   — optional; triggers a live fetch from the provider API
          api_base  — optional; Ollama base URL override
        """
        provider = request.args.get("provider", "google")
        api_key  = request.args.get("api_key", "").strip()
        api_base = request.args.get("api_base", "").strip()

        if not api_key:
            env_var = PROVIDERS.get(provider, {}).get("env_var")
            if env_var:
                api_key = os.getenv(env_var, "")

        return jsonify(get_models(provider, api_key, api_base))

    # ------------------------------------------------------------------
    # Scrape
    # ------------------------------------------------------------------

    @app.route("/api/scrape", methods=["POST"])
    def api_scrape():
        """
        Start a scrape job.

        JSON body:
          url, provider, model, api_key, fields (list), format
        Returns:
          {"job_id": "<uuid>"}
        """
        body     = request.get_json(force=True) or {}
        url      = (body.get("url") or "").strip()
        provider = body.get("provider", "google")
        model    = body.get("model", "")
        api_key  = (body.get("api_key") or "").strip()
        fields   = body.get("fields") or []
        fmt      = body.get("format", "json")

        if not url:
            return jsonify({"error": "URL is required"}), 400
        if not model:
            return jsonify({"error": "Model is required"}), 400

        if not api_key:
            env_var = PROVIDERS.get(provider, {}).get("env_var")
            if env_var:
                api_key = os.getenv(env_var, "")

        job = Job()
        jobs[job.job_id] = job

        threading.Thread(
            target=run_job,
            args=(job, url, provider, model, api_key, fields, fmt),
            daemon=True,
        ).start()

        return jsonify({"job_id": job.job_id})

    # ------------------------------------------------------------------
    # Log stream (SSE)
    # ------------------------------------------------------------------

    @app.route("/api/stream/<job_id>")
    def api_stream(job_id: str):
        """
        Server-Sent Events endpoint.
        Streams log entries for *job_id* until the job completes.
        """
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        def _generate():
            while True:
                try:
                    entry = job.log_queue.get(timeout=25)
                except queue.Empty:
                    yield 'data: {"type":"keepalive"}\n\n'
                    if job.done.is_set():
                        break
                    continue

                if entry.get("type") == "done":
                    payload = json.dumps({
                        "type":   "done",
                        "result": job.result,
                        "error":  job.error,
                    })
                    yield f"data: {payload}\n\n"
                    break

                yield f"data: {json.dumps(entry)}\n\n"

        return Response(
            stream_with_context(_generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control":    "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app
