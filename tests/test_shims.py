"""Tests for thin shim modules: browsegenie/mcp_server.py and browsegenie/web_ui.py."""

import inspect
from unittest.mock import AsyncMock, patch


class TestMcpServerShim:
    """Tests for the mcp_server.py entry-point shim."""

    def test_main_sync_calls_asyncio_run(self):
        """Test that main_sync() calls asyncio.run() with the main coroutine."""
        with patch(
            "browsegenie.mcp_server.create_and_run_server",
            new_callable=AsyncMock,
        ) as mock_server:
            from browsegenie.mcp_server import main_sync
            main_sync()
            mock_server.assert_called_once()

    def test_main_is_coroutine(self):
        """Test that main() is an async function that can be awaited."""
        from browsegenie.mcp_server import main
        assert inspect.iscoroutinefunction(main)


class TestWebUiShim:
    """Tests for the web_ui.py re-export shim."""

    def test_create_app_exported(self):
        """Test that create_app is importable from the browsegenie.web_ui shim."""
        from browsegenie.web_ui import create_app
        assert callable(create_app)

    def test_main_exported(self):
        """Test that main is importable from the browsegenie.web_ui shim."""
        from browsegenie.web_ui import main
        assert callable(main)

    def test_all_lists_expected_names(self):
        """Test that __all__ contains both 'main' and 'create_app'."""
        import browsegenie.web_ui as shim
        assert "main" in shim.__all__
        assert "create_app" in shim.__all__
