"""
webagent.web_ui
~~~~~~~~~~~~~~~~~~~~~~~~
Thin shim that preserves the `webagent-ui` console-script entry point.

All implementation lives in webagent/core/web_ui/.
"""

from .core.web_ui import create_app, main  # noqa: F401

__all__ = ["main", "create_app"]
