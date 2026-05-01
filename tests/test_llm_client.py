"""Tests for LLMClient and _normalize_model in browser_agent/agent/llm.py."""

from unittest.mock import MagicMock, patch

from browsegenie.core.browser_agent.agent.llm import LLMClient, _normalize_model


class TestNormalizeModel:
    """Tests for the _normalize_model() routing-prefix helper."""

    def test_google_prefix_added(self):
        """Test that provider='google' prepends 'gemini/' to the model name."""
        assert _normalize_model("google", "gemini-flash") == "gemini/gemini-flash"

    def test_ollama_prefix_added(self):
        """Test that provider='ollama' prepends 'ollama/' to the model name."""
        assert _normalize_model("ollama", "llama3") == "ollama/llama3"

    def test_deepseek_prefix_added(self):
        """Test that provider='deepseek' prepends 'deepseek/' to the model name."""
        assert _normalize_model("deepseek", "deepseek-chat") == "deepseek/deepseek-chat"

    def test_mistral_prefix_added(self):
        """Test that provider='mistral' prepends 'mistral/' to the model name."""
        assert _normalize_model("mistral", "mistral-7b") == "mistral/mistral-7b"

    def test_cohere_prefix_added(self):
        """Test that provider='cohere' prepends 'cohere/' to the model name."""
        assert _normalize_model("cohere", "command-r") == "cohere/command-r"

    def test_xai_prefix_added(self):
        """Test that provider='xai' prepends 'xai/' to the model name."""
        assert _normalize_model("xai", "grok-2") == "xai/grok-2"

    def test_already_prefixed_not_doubled(self):
        """Test that a model already starting with the expected prefix is not double-prefixed."""
        assert _normalize_model("google", "gemini/gemini-flash") == "gemini/gemini-flash"

    def test_unknown_provider_passthrough(self):
        """Test that an unrecognised provider leaves the model name unchanged."""
        assert _normalize_model("openai", "gpt-4o") == "gpt-4o"

    def test_empty_provider_passthrough(self):
        """Test that an empty provider string leaves the model name unchanged."""
        assert _normalize_model("", "gpt-4o") == "gpt-4o"


class TestLLMClient:
    """Tests for the LLMClient wrapper around litellm."""

    def setup_method(self):
        """Create a fresh LLMClient for each test."""
        self.client = LLMClient(model="gpt-4o", provider="openai", api_key="sk-test")

    def _mock_response(self, content="ok"):
        """Return a mock litellm response object with a single choice."""
        resp = MagicMock()
        resp.choices[0].message.content = content
        return resp

    def test_model_property_reflects_normalized_name(self):
        """Test that the model property returns the provider-prefixed model name."""
        client = LLMClient(model="gemini-flash", provider="google")
        assert client.model == "gemini/gemini-flash"

    def test_model_property_openai_no_prefix(self):
        """Test that openai models pass through without a prefix because openai is not in PROVIDER_PREFIXES."""
        client = LLMClient(model="gpt-4o", provider="openai")
        assert client.model == "gpt-4o"

    def test_complete_calls_litellm(self):
        """Test that complete() calls litellm.completion with model, messages, tools, and api_key."""
        with patch(
            "browsegenie.core.browser_agent.agent.llm.litellm.completion"
        ) as mock_comp:
            mock_comp.return_value = self._mock_response()
            self.client.complete(
                messages=[{"role": "user", "content": "hi"}],
                tools=[{"name": "t"}],
            )
            kwargs = mock_comp.call_args[1]
            assert kwargs["model"] == "gpt-4o"
            assert kwargs["api_key"] == "sk-test"
            assert "tools" in kwargs

    def test_complete_no_api_key_omits_api_key_kwarg(self):
        """Test that complete() omits the api_key kwarg when no key was provided."""
        client = LLMClient(model="gpt-4o")
        with patch(
            "browsegenie.core.browser_agent.agent.llm.litellm.completion"
        ) as mock_comp:
            mock_comp.return_value = self._mock_response()
            client.complete(messages=[], tools=[])
            assert "api_key" not in mock_comp.call_args[1]

    def test_complete_text_returns_content_string(self):
        """Test that complete_text() returns the content string from the first choice."""
        with patch(
            "browsegenie.core.browser_agent.agent.llm.litellm.completion"
        ) as mock_comp:
            mock_comp.return_value = self._mock_response(content="Hello World")
            result = self.client.complete_text(
                messages=[{"role": "user", "content": "say hi"}]
            )
            assert result == "Hello World"

    def test_token_stats_returns_dict(self):
        """Test that token_stats() returns a dict summarising usage."""
        stats = self.client.token_stats()
        assert isinstance(stats, dict)

    def test_token_stats_accumulate_across_calls(self):
        """Test that token usage is accumulated from multiple complete() calls."""
        from browsegenie.core.token_usage import ApiCallTokens

        with patch(
            "browsegenie.core.browser_agent.agent.llm.litellm.completion"
        ) as mock_comp, patch(
            "browsegenie.core.browser_agent.agent.llm.extract_litellm_tokens"
        ) as mock_tok:
            mock_comp.return_value = self._mock_response()
            mock_tok.return_value = ApiCallTokens(
                model="gpt-4o", prompt_tokens=10, completion_tokens=5, total_tokens=15
            )
            self.client.complete(messages=[], tools=[])
            self.client.complete(messages=[], tools=[])
            assert len(self.client._calls) == 2

    def test_none_tokens_not_appended(self):
        """Test that a None token result from extract_litellm_tokens is not added to _calls."""
        with patch(
            "browsegenie.core.browser_agent.agent.llm.litellm.completion"
        ) as mock_comp, patch(
            "browsegenie.core.browser_agent.agent.llm.extract_litellm_tokens"
        ) as mock_tok:
            mock_comp.return_value = self._mock_response()
            mock_tok.return_value = None
            self.client.complete(messages=[], tools=[])
            assert self.client._calls == []
