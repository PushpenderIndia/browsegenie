"""
CLI entry point for the WebAgent Web UI.

Invoked via the `webagent-ui` console script.
"""

import argparse
import logging
import socket
import sys
import threading
import time
import webbrowser


def _find_free_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    """Return the first free TCP port starting from *start_port*."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError(
        f"No free port found between {start_port} and "
        f"{start_port + max_attempts - 1}. Stop one of those services and retry."
    )


def main() -> None:
    try:
        from flask import Flask  # noqa: F401
    except ImportError:
        print("Error: Flask is required for the web UI.")
        print("Install it with: pip install flask")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        prog="webagent-ui",
        description="WebAgent — local web UI",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7860, help="Port (default: 7860)")
    parser.add_argument("--no-browser", action="store_true", help="Skip auto-opening browser")
    args = parser.parse_args()

    try:
        port = _find_free_port(args.host, args.port)
    except OSError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    if port != args.port:
        print(f"  Port {args.port} is in use — using port {port} instead.")

    server_url = f"http://{args.host}:{port}"

    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║      WebAgent  Web UI       ║")
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
        port=port,
        threaded=True,
        debug=False,
        use_reloader=False,
    )
