"""LLM client with provider-prefix normalisation and per-session token tracking."""

from typing import Any, Dict, List, Optional

import litellm

from ....core.token_usage import ApiCallTokens, extract_litellm_tokens, summarise


# Some providers require a routing prefix that LiteLLM expects but callers
# typically omit.  e.g. provider="google", model="gemini-flash"
#   → normalised to "gemini/gemini-flash"
_PROVIDER_PREFIXES: Dict[str, str] = {
    "google":   "gemini/",
    "ollama":   "ollama/",
    "deepseek": "deepseek/",
    "mistral":  "mistral/",
    "cohere":   "cohere/",
    "xai":      "xai/",
}


def _normalize_model(provider: str, model: str) -> str:
    prefix = _PROVIDER_PREFIXES.get(provider, "")
    if prefix and not model.startswith(prefix):
        return prefix + model
    return model


class LLMClient:
    """Wraps LiteLLM for tool-use completions and accumulates token usage across calls."""

    def __init__(
        self,
        model: str,
        provider: str = "",
        api_key: Optional[str] = None,
    ) -> None:
        self._model        = _normalize_model(provider, model)
        self._api_key      = api_key
        self._calls: List[ApiCallTokens] = []

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: List[Dict], tools: List[Dict]) -> Any:
        kwargs: Dict[str, Any] = {
            "model":       self._model,
            "messages":    messages,
            "tools":       tools,
            "tool_choice": "auto",
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        response = litellm.completion(**kwargs)
        tokens = extract_litellm_tokens(response, self._model)
        if tokens:
            self._calls.append(tokens)
        return response

    def token_stats(self) -> Dict[str, Any]:
        """Return cumulative token usage across all calls this session."""
        return summarise(self._calls)
