"""
Flask application factory and API route definitions.

Static files are served from  core/web_ui/static/
HTML template is served from  core/web_ui/templates/index.html

Routes
------
GET  /                           → SPA (index.html)
GET  /static/<path>              → CSS / JS assets
GET  /api/providers              → provider metadata
GET  /api/models                 → model list for a provider
POST /api/scrape                 → start scrape job (single or multi-URL)
GET  /api/stream/<job_id>        → SSE: scrape job log stream
POST /api/agent/plan             → start AI agent planning task
GET  /api/agent/stream/<task_id> → SSE: agent step stream
"""

import json
import logging
import os
import queue
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from ... import __version__
from .jobs import Job, jobs, run_job, run_multi_url_job
from .providers import PROVIDERS, get_models

_WEB_UI_DIR = Path(__file__).parent


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(_WEB_UI_DIR / "templates"),
        static_folder=str(_WEB_UI_DIR / "static"),
        static_url_path="/static",
    )
    app.logger.setLevel(logging.WARNING)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return render_template("index.html", version=__version__)

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    @app.route("/api/providers")
    def api_providers():
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
        provider = request.args.get("provider", "google")
        api_key  = request.args.get("api_key", "").strip()
        api_base = request.args.get("api_base", "").strip()

        if not api_key:
            env_var = PROVIDERS.get(provider, {}).get("env_var")
            if env_var:
                api_key = os.getenv(env_var, "")

        return jsonify(get_models(provider, api_key, api_base))

    # ------------------------------------------------------------------
    # Scrape  (single-URL + multi-URL)
    # ------------------------------------------------------------------

    @app.route("/api/scrape", methods=["POST"])
    def api_scrape():
        """
        Start a scrape job.

        Body (JSON):
          urls     – list of URLs  [preferred]
          url      – single URL    [legacy]
          provider, model, api_key, fields, format
        """
        body     = request.get_json(force=True) or {}
        urls     = body.get("urls") or []
        url      = (body.get("url") or "").strip()
        provider = body.get("provider", "google")
        model    = body.get("model", "")
        api_key  = (body.get("api_key") or "").strip()
        fields   = body.get("fields") or []
        fmt      = body.get("format", "json")

        # Normalise: prefer `urls`, fall back to single `url`
        if not urls and url:
            urls = [url]
        urls = [u.strip() for u in urls if u and u.strip()]

        if not urls:
            return jsonify({"error": "At least one URL is required"}), 400
        if not model:
            return jsonify({"error": "Model is required"}), 400

        if not api_key:
            env_var = PROVIDERS.get(provider, {}).get("env_var")
            if env_var:
                api_key = os.getenv(env_var, "")

        job = Job()
        jobs[job.job_id] = job

        if len(urls) == 1:
            threading.Thread(
                target=run_job,
                args=(job, urls[0], provider, model, api_key, fields, fmt),
                daemon=True,
            ).start()
        else:
            threading.Thread(
                target=run_multi_url_job,
                args=(job, urls, provider, model, api_key, fields, fmt),
                daemon=True,
            ).start()

        return jsonify({"job_id": job.job_id})

    # ------------------------------------------------------------------
    # Scrape log stream (SSE)
    # ------------------------------------------------------------------

    @app.route("/api/stream/<job_id>")
    def api_stream(job_id: str):
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
                    yield f"data: {json.dumps({'type':'done','result':job.result,'error':job.error})}\n\n"
                    break

                yield f"data: {json.dumps(entry)}\n\n"

        return Response(
            stream_with_context(_generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ------------------------------------------------------------------
    # Agent: start plan
    # ------------------------------------------------------------------

    @app.route("/api/agent/plan", methods=["POST"])
    def api_agent_plan():
        """
        Body (JSON):
          requirement – natural-language description
          provider, model, api_key
        """
        body        = request.get_json(force=True) or {}
        requirement = (body.get("requirement") or "").strip()
        provider    = body.get("provider", "google")
        model       = body.get("model", "")
        api_key     = (body.get("api_key") or "").strip()

        if not requirement:
            return jsonify({"error": "requirement is required"}), 400

        if not api_key:
            env_var = PROVIDERS.get(provider, {}).get("env_var")
            if env_var:
                api_key = os.getenv(env_var, "")

        from browsegenie.core.agent import start_plan
        task = start_plan(requirement, provider, model or "gemini-2.5-flash", api_key)
        return jsonify({"task_id": task.task_id})

    # ------------------------------------------------------------------
    # Agent: event stream (SSE)
    # ------------------------------------------------------------------

    @app.route("/api/agent/stream/<task_id>")
    def api_agent_stream(task_id: str):
        from browsegenie.core.agent import agent_tasks
        task = agent_tasks.get(task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404

        def _generate():
            while True:
                try:
                    entry = task.log_queue.get(timeout=25)
                except queue.Empty:
                    yield 'data: {"type":"keepalive"}\n\n'
                    if task.done.is_set():
                        break
                    continue

                yield f"data: {json.dumps(entry)}\n\n"
                if entry.get("type") == "done":
                    break

        return Response(
            stream_with_context(_generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ------------------------------------------------------------------
    # Browser Agent: start session
    # ------------------------------------------------------------------

    @app.route("/api/browser-agent/start", methods=["POST"])
    def api_browser_agent_start():
        body         = request.get_json(force=True) or {}
        task         = (body.get("task") or "").strip()
        provider     = body.get("provider", "google")
        model        = body.get("model", "")
        api_key      = (body.get("api_key") or "").strip()
        headless     = body.get("headless", True)
        control_mode = body.get("control_mode", "shared")

        if not task:
            return jsonify({"error": "task is required"}), 400
        if not model:
            return jsonify({"error": "model is required"}), 400

        if not api_key:
            env_var = PROVIDERS.get(provider, {}).get("env_var")
            if env_var:
                api_key = os.getenv(env_var, "")

        from browsegenie.core.browser_agent.agent.sessions import create_session
        session = create_session(
            task=task,
            model=model,
            provider=provider,
            api_key=api_key,
            headless=headless,
            control_mode=control_mode,
        )
        return jsonify({"session_id": session.session_id})

    # ------------------------------------------------------------------
    # Browser Agent: event stream (SSE)
    # ------------------------------------------------------------------

    @app.route("/api/browser-agent/stream/<session_id>")
    def api_browser_agent_stream(session_id: str):
        from browsegenie.core.browser_agent.agent.sessions import get_session
        session = get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404

        def _generate():
            while True:
                try:
                    event = session.event_queue.get(timeout=25)
                except queue.Empty:
                    yield 'data: {"type":"keepalive"}\n\n'
                    if session.is_done:
                        break
                    continue

                yield f"data: {json.dumps(event)}\n\n"

                if event.get("type") in ("done", "error"):
                    break

        return Response(
            stream_with_context(_generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ------------------------------------------------------------------
    # Browser Agent: stop session
    # ------------------------------------------------------------------

    @app.route("/api/browser-agent/stop/<session_id>", methods=["POST"])
    def api_browser_agent_stop(session_id: str):
        from browsegenie.core.browser_agent.agent.sessions import get_session
        session = get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        session.stop()
        return jsonify({"status": "stopped"})

    # ------------------------------------------------------------------
    # Browser Agent: playback frames
    # ------------------------------------------------------------------

    @app.route("/api/browser-agent/playback/<session_id>")
    def api_browser_agent_playback(session_id: str):
        from browsegenie.core.browser_agent.agent.sessions import get_session
        session = get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        frames = session.get_playback_frames()
        return jsonify({"frames": frames, "total": len(frames)})

    # ------------------------------------------------------------------
    # Browser Agent: human control
    #
    # POST /api/browser-agent/control/<session_id>
    # Body: { "action": "click", "payload": { "x": 120, "y": 340 } }
    #
    # Supported actions:
    #   click    { x, y }
    #   type     { text }
    #   press_key{ key }
    #   navigate { url }
    #   scroll   { dx, dy }
    # ------------------------------------------------------------------

    @app.route("/api/browser-agent/control/<session_id>", methods=["POST"])
    def api_browser_agent_control(session_id: str):
        from browsegenie.core.browser_agent.agent.sessions import get_session
        session = get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404

        body    = request.get_json(force=True) or {}
        action  = (body.get("action") or "").strip()
        payload = body.get("payload") or {}

        if not action:
            return jsonify({"error": "action is required"}), 400

        result = session.execute_control(action, payload)
        return jsonify(result)

    # ------------------------------------------------------------------
    # Browser Agent: control mode
    #
    # GET  /api/browser-agent/mode/<session_id>      → { mode }
    # POST /api/browser-agent/mode/<session_id>      body: { mode }
    # ------------------------------------------------------------------

    @app.route("/api/browser-agent/mode/<session_id>", methods=["GET", "POST"])
    def api_browser_agent_mode(session_id: str):
        from browsegenie.core.browser_agent.agent.sessions import get_session
        session = get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404

        if request.method == "GET":
            return jsonify({"mode": session.get_mode()})

        body = request.get_json(force=True) or {}
        mode = (body.get("mode") or "shared").strip()
        try:
            session.set_mode(mode)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"mode": session.get_mode()})

    return app
