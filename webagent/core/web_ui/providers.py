"""
Provider metadata and dynamic model-fetching logic.

Supports Google Gemini, OpenAI, Anthropic, and Ollama.
Models are fetched live from provider APIs when an API key is present,
falling back to litellm's bundled model registry otherwise.
"""

import os
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS: Dict[str, Any] = {
    "google": {
        "name": "Google Gemini",
        "litellm_key": "gemini",
        "env_var": "GEMINI_API_KEY",
        "placeholder": "AIza...",
        "docs_url": "https://aistudio.google.com/app/apikey",
    },
    "openai": {
        "name": "OpenAI",
        "litellm_key": "openai",
        "env_var": "OPENAI_API_KEY",
        "placeholder": "sk-...",
        "docs_url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "litellm_key": "anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "placeholder": "sk-ant-...",
        "docs_url": "https://console.anthropic.com/",
    },
    "ollama": {
        "name": "Ollama (Local)",
        "litellm_key": "ollama",
        "env_var": None,
        "placeholder": "Not required for local Ollama",
        "docs_url": "https://ollama.ai/",
    },
}

# ---------------------------------------------------------------------------
# Model filtering
# ---------------------------------------------------------------------------

# Substrings that identify non-text-chat models (image, audio, video, etc.)
_EXCLUDE_PATTERNS = (
    # Embeddings
    "embed", "embedding", "text-search", "text-similarity", "code-search",
    # Image generation / image-specific
    "dall-e", "imagen", "image-generation", "-image",
    # Audio / speech / transcription
    "tts", "whisper", "audio", "speech", "transcription", "transcribe",
    # Video generation
    "veo", "sora",
    # Music generation
    "lyria",
    # Realtime / live streaming
    "realtime", "live",
    # Moderation
    "moderation",
    # Legacy completion models (non-chat)
    "babbage", "davinci",
    # Misc non-text
    "aqa", "visiontext", "robotics", "computer-use", "deep-research",
    "container",
    # Fine-tuning placeholders
    "ft:",
)

# Model name prefixes ordered by approximate release date, newest first.
# Handles both bare names ("gemini-2.0-flash") and LiteLLM-prefixed names
# ("gemini/gemini-2.0-flash") — matching is done after stripping any "provider/" prefix.
_MODEL_RELEASE_ORDER = [
    # ── Google Gemini 2.5  (2025) ──────────────────────────────────────────
    "gemini-2.5-pro-exp", "gemini-2.5-pro-preview", "gemini-2.5-pro",
    "gemini-2.5-flash-preview", "gemini-2.5-flash",
    "gemini-2.5",
    # ── Google Gemini 2.0  (early 2025) ───────────────────────────────────
    "gemini-2.0-flash-thinking", "gemini-2.0-flash-lite", "gemini-2.0-flash-exp",
    "gemini-2.0-flash", "gemini-2.0-pro-exp", "gemini-2.0",
    # ── OpenAI o3 / o4  (2025) ────────────────────────────────────────────
    "o4-mini", "o3-pro", "o3-mini-high", "o3-mini", "o3",
    # ── OpenAI GPT-4.5  (2025) ────────────────────────────────────────────
    "gpt-4.5-turbo", "gpt-4.5-preview", "gpt-4.5",
    # ── Anthropic Claude 4  (2025) ────────────────────────────────────────
    "claude-opus-4-5", "claude-opus-4",
    "claude-sonnet-4-5", "claude-sonnet-4",
    "claude-haiku-4-5", "claude-haiku-4",
    # ── OpenAI o1  (2024) ─────────────────────────────────────────────────
    "o1-pro", "o1-preview", "o1-mini", "o1",
    # ── OpenAI GPT-4o  (2024) ─────────────────────────────────────────────
    "gpt-4o-mini-audio", "gpt-4o-audio", "gpt-4o-mini", "gpt-4o",
    # ── Anthropic Claude 3.5  (2024) ──────────────────────────────────────
    "claude-3-5-sonnet", "claude-3-5-haiku", "claude-3-5",
    # ── Google Gemini 1.5  (2024) ─────────────────────────────────────────
    "gemini-1.5-pro", "gemini-1.5-flash-8b", "gemini-1.5-flash", "gemini-1.5",
    # ── OpenAI GPT-4 Turbo  (2024) ────────────────────────────────────────
    "gpt-4-turbo-preview", "gpt-4-turbo",
    # ── Anthropic Claude 3  (2024) ────────────────────────────────────────
    "claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-3",
    # ── Google Gemini 1.0 / Pro  (2023) ───────────────────────────────────
    "gemini-1.0-pro", "gemini-pro",
    # ── OpenAI GPT-4  (2023) ──────────────────────────────────────────────
    "gpt-4-32k", "gpt-4",
    # ── OpenAI GPT-3.5  (2022) ────────────────────────────────────────────
    "gpt-3.5-turbo-instruct", "gpt-3.5-turbo", "gpt-3.5",
]

# Pre-build a rank lookup for O(1) access
_MODEL_RANK: Dict[str, int] = {name: i for i, name in enumerate(_MODEL_RELEASE_ORDER)}


def _model_sort_key(model: str) -> tuple:
    """
    Sort key: (tier, rank, name)
    - tier 0 → matched a known release; rank = position in _MODEL_RELEASE_ORDER
    - tier 1 → unrecognised; sorted alphabetically
    Handles LiteLLM-prefixed names like "gemini/gemini-2.0-flash".
    """
    bare = model.split("/")[-1].lower()
    for prefix, rank in _MODEL_RANK.items():
        if bare.startswith(prefix):
            return (0, rank, model)
    return (1, len(_MODEL_RELEASE_ORDER), model)


def _is_chat_model(name: str) -> bool:
    """Return True if the model looks like a text-chat/completion model."""
    lower = name.lower()
    return not any(pat in lower for pat in _EXCLUDE_PATTERNS)


def _sort_models(models: List[str]) -> List[str]:
    """Sort models newest-first by release date, then alphabetically for unknowns."""
    return sorted(models, key=_model_sort_key)


# ---------------------------------------------------------------------------
# Static fallback (litellm bundled registry)
# ---------------------------------------------------------------------------

def _models_from_litellm(litellm_key: str) -> List[str]:
    """
    Return chat models for *litellm_key* from litellm.models_by_provider.
    No network call — uses the registry bundled with the installed litellm.
    """
    try:
        import litellm
        raw: set = litellm.models_by_provider.get(litellm_key, set())
        return _sort_models([m for m in raw if _is_chat_model(m)])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Live fetchers (one per provider)
# ---------------------------------------------------------------------------

def _models_live_google(api_key: str) -> List[str]:
    try:
        from litellm.llms.gemini.common_utils import GeminiModelInfo
        models = GeminiModelInfo().get_models(api_key=api_key)
        return _sort_models([m for m in models if _is_chat_model(m)])
    except Exception:
        return []


def _models_live_openai(api_key: str) -> List[str]:
    try:
        from litellm.llms.openai.chat.gpt_transformation import OpenAIGPTConfig
        models = OpenAIGPTConfig().get_models(api_key=api_key)
        return _sort_models([m for m in models if _is_chat_model(m)])
    except Exception:
        return []


def _models_live_anthropic(api_key: str) -> List[str]:
    try:
        from litellm.llms.anthropic.common_utils import AnthropicModelInfo
        models = AnthropicModelInfo().get_models(api_key=api_key)
        return _sort_models([m for m in models if _is_chat_model(m)])
    except Exception:
        return []


def _models_live_ollama(api_base: str = "http://localhost:11434") -> List[str]:
    try:
        from litellm.llms.ollama.common_utils import OllamaModelInfo
        return _sort_models(OllamaModelInfo().get_models(api_base=api_base))
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_LIVE_FETCHERS = {
    "google":    _models_live_google,
    "openai":    _models_live_openai,
    "anthropic": _models_live_anthropic,
}


def get_models(provider: str, api_key: str = "", api_base: str = "") -> Dict[str, Any]:
    """
    Return ``{"models": [...]}`` for *provider*.

    Strategy:
    - Ollama  → always queries localhost (no key needed)
    - Others  → live API fetch when *api_key* supplied, litellm fallback otherwise
    """
    cfg = PROVIDERS.get(provider, {})
    litellm_key = cfg.get("litellm_key", provider)

    if provider == "ollama":
        base = api_base or os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        models = _models_live_ollama(base) or _models_from_litellm(litellm_key)
        return {"models": models}

    if api_key and provider in _LIVE_FETCHERS:
        models = _LIVE_FETCHERS[provider](api_key)
        if models:
            return {"models": models}

    return {"models": _models_from_litellm(litellm_key)}
