"""
CLI entry point for the Universal Scraper Web UI.

Invoked via the `universal-scraper-ui` console script.
"""

import argparse
import logging
import sys
import threading
import time
import webbrowser


def main() -> None:
    try:
        from flask import Flask  # noqa: F401
    except ImportError:
        print("Error: Flask is required for the web UI.")
        print("Install it with: pip install flask")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        prog="universal-scraper-ui",
        description="Universal Scraper — local web UI",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7860, help="Port (default: 7860)")
    parser.add_argument("--no-browser", action="store_true", help="Skip auto-opening browser")
    args = parser.parse_args()

    server_url = f"http://{args.host}:{args.port}"

    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║      Universal Scraper  Web UI       ║")
    print("  ╚══════════════════════════════════════╝")
    print(f"  Server  →  {server_url}")
    print("  Press Ctrl+C to stop.")
    print()

    if not args.no_browser:
        def _open_browser() -> None:
            time.sleep(1.4)
            webbrowser.open(server_url)

        threading.Thread(target=_open_browser, daemon=True).start()

    # Suppress noisy Werkzeug request logs
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    from .server import create_app
    app = create_app()
    app.run(
        host=args.host,
        port=args.port,
        threaded=True,
        debug=False,
        use_reloader=False,
    )
