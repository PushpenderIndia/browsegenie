"""Tests for web UI providers: PROVIDERS dict, get_models(), and helper functions."""

from unittest.mock import MagicMock, patch

from browsegenie.core.web_ui.providers import (
    PROVIDERS,
    _is_chat_model,
    _model_sort_key,
    _models_from_litellm,
    get_models,
)


class TestProvidersRegistry:
    """Tests for the PROVIDERS constant."""

    def test_providers_contains_google(self):
        """Test that the google provider is registered in PROVIDERS."""
        assert "google" in PROVIDERS

    def test_providers_contains_openai(self):
        """Test that the openai provider is registered in PROVIDERS."""
        assert "openai" in PROVIDERS

    def test_providers_contains_anthropic(self):
        """Test that the anthropic provider is registered in PROVIDERS."""
        assert "anthropic" in PROVIDERS

    def test_providers_contains_ollama(self):
        """Test that the ollama provider is registered in PROVIDERS."""
        assert "ollama" in PROVIDERS

    def test_each_provider_has_name_and_litellm_key(self):
        """Test that every provider entry has both a name and a litellm_key field."""
        for key, cfg in PROVIDERS.items():
            assert "name" in cfg, f"Provider '{key}' missing 'name'"
            assert "litellm_key" in cfg, f"Provider '{key}' missing 'litellm_key'"


class TestIsChatModel:
    """Tests for the _is_chat_model() filter."""

    def test_gpt4o_is_chat_model(self):
        """Test that gpt-4o is identified as a chat model."""
        assert _is_chat_model("gpt-4o") is True

    def test_gemini_flash_is_chat_model(self):
        """Test that gemini-2.5-flash is identified as a chat model."""
        assert _is_chat_model("gemini-2.5-flash") is True

    def test_claude_haiku_is_chat_model(self):
        """Test that claude-3-haiku is identified as a chat model."""
        assert _is_chat_model("claude-3-haiku-20240307") is True

    def test_embedding_model_excluded(self):
        """Test that embedding models are not considered chat models."""
        assert _is_chat_model("text-embedding-ada-002") is False

    def test_dalle_excluded(self):
        """Test that DALL-E image generation models are excluded."""
        assert _is_chat_model("dall-e-3") is False

    def test_tts_excluded(self):
        """Test that text-to-speech models are excluded."""
        assert _is_chat_model("tts-1") is False

    def test_whisper_excluded(self):
        """Test that Whisper transcription models are excluded."""
        assert _is_chat_model("whisper-1") is False


class TestModelSortKey:
    """Tests for the _model_sort_key() sort helper."""

    def test_known_model_returns_tier_zero(self):
        """Test that a recognised model name gets tier 0 (known release order)."""
        key = _model_sort_key("gemini-2.5-flash")
        assert key[0] == 0

    def test_unknown_model_returns_tier_one(self):
        """Test that an unrecognised model name gets tier 1 (alphabetical fallback)."""
        key = _model_sort_key("completely-unknown-model-xyz")
        assert key[0] == 1

    def test_newer_model_sorts_before_older(self):
        """Test that a newer model has a lower sort key than an older model."""
        new_key = _model_sort_key("gemini-2.5-flash")
        old_key = _model_sort_key("gemini-1.0-pro")
        assert new_key < old_key

    def test_litellm_prefixed_name_resolved(self):
        """Test that litellm-prefixed names like 'gemini/gemini-2.0-flash' are resolved correctly."""
        key = _model_sort_key("gemini/gemini-2.0-flash")
        assert key[0] == 0


class TestModelsFromLitellm:
    """Tests for the _models_from_litellm() static fallback."""

    def test_returns_list(self):
        """Test that _models_from_litellm returns a list for a known provider key."""
        import litellm
        original = litellm.models_by_provider
        try:
            litellm.models_by_provider = {
                "openai": {"gpt-4o", "gpt-3.5-turbo", "dall-e-3"}
            }
            result = _models_from_litellm("openai")
        finally:
            litellm.models_by_provider = original
        assert isinstance(result, list)
        assert "dall-e-3" not in result

    def test_returns_empty_list_on_exception(self):
        """Test that _models_from_litellm returns an empty list if an exception is raised."""
        import litellm

        class _Explode:
            def get(self, key, default):
                raise RuntimeError("boom")

        original = litellm.models_by_provider
        try:
            litellm.models_by_provider = _Explode()
            result = _models_from_litellm("openai")
        finally:
            litellm.models_by_provider = original
        assert result == []


class TestGetModels:
    """Tests for the public get_models() function."""

    def test_returns_dict_with_models_key(self):
        """Test that get_models returns a dict with a 'models' key."""
        with patch("browsegenie.core.web_ui.providers._models_from_litellm", return_value=["gpt-4o"]):
            result = get_models("openai")
        assert "models" in result
        assert isinstance(result["models"], list)

    def test_live_fetch_used_when_api_key_provided(self):
        """Test that the live fetcher is called when an api_key is supplied for a supported provider."""
        import browsegenie.core.web_ui.providers as prov_mod
        mock_live = MagicMock(return_value=["gpt-4o-mini"])
        original = prov_mod._LIVE_FETCHERS.get("openai")
        try:
            prov_mod._LIVE_FETCHERS["openai"] = mock_live
            result = get_models("openai", api_key="sk-test")
        finally:
            prov_mod._LIVE_FETCHERS["openai"] = original
        mock_live.assert_called_once_with("sk-test")
        assert "gpt-4o-mini" in result["models"]

    def test_litellm_fallback_when_no_api_key(self):
        """Test that the litellm static registry is used when no api_key is supplied."""
        with patch(
            "browsegenie.core.web_ui.providers._models_from_litellm",
            return_value=["gpt-4o"],
        ) as mock_static:
            get_models("openai")
        mock_static.assert_called()

    def test_litellm_fallback_when_live_fetch_empty(self):
        """Test that the litellm fallback is used when the live fetch returns an empty list."""
        with patch(
            "browsegenie.core.web_ui.providers._models_live_openai",
            return_value=[],
        ), patch(
            "browsegenie.core.web_ui.providers._models_from_litellm",
            return_value=["gpt-4o"],
        ) as mock_static:
            result = get_models("openai", api_key="sk-key")
        mock_static.assert_called()
        assert "gpt-4o" in result["models"]

    def test_ollama_uses_live_fetcher(self):
        """Test that ollama always calls the live fetcher regardless of api_key."""
        with patch(
            "browsegenie.core.web_ui.providers._models_live_ollama",
            return_value=["llama3"],
        ) as mock_ollama:
            result = get_models("ollama")
        mock_ollama.assert_called()
        assert "llama3" in result["models"]

    def test_unknown_provider_returns_litellm_fallback(self):
        """Test that an unregistered provider falls back to the litellm static registry."""
        with patch(
            "browsegenie.core.web_ui.providers._models_from_litellm",
            return_value=[],
        ):
            result = get_models("unknown_provider")
        assert "models" in result
