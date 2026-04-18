"""
Token usage tracking for Universal Scraper AI API calls.

Provides dataclasses and helpers to capture, accumulate, and summarise
token consumption from both the Google Gemini (google-genai) and
LiteLLM backends.

Usage inside DataExtractor
--------------------------
    from .token_usage import ApiCallTokens, extract_gemini_tokens, \
                             extract_litellm_tokens, summarise

    # After a Gemini call:
    tokens = extract_gemini_tokens(response, model_name)
    if tokens:
        self._token_calls.append(tokens)

    # After a LiteLLM call:
    tokens = extract_litellm_tokens(response, model_name)
    if tokens:
        self._token_calls.append(tokens)

    # To expose the summary to callers:
    def get_token_usage(self):
        return summarise(self._token_calls)
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Per-call record
# ---------------------------------------------------------------------------

@dataclass
class ApiCallTokens:
    """Token counts for a single AI API call."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    from_cache: bool = False   # True  → code came from cache, no API call made

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def extract_gemini_tokens(response: Any, model: str) -> Optional[ApiCallTokens]:
    """
    Extract token counts from a ``google.genai`` GenerateContentResponse.

    The SDK exposes usage via ``response.usage_metadata`` with attributes:
      - ``prompt_token_count``
      - ``candidates_token_count``
      - ``total_token_count``
    """
    try:
        um = getattr(response, "usage_metadata", None)
        if um is None:
            return None
        prompt     = getattr(um, "prompt_token_count",     0) or 0
        completion = getattr(um, "candidates_token_count", 0) or 0
        total      = getattr(um, "total_token_count",      0) or (prompt + completion)
        return ApiCallTokens(
            model=model,
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )
    except Exception:
        return None


def extract_litellm_tokens(response: Any, model: str) -> Optional[ApiCallTokens]:
    """
    Extract token counts from a LiteLLM ``ModelResponse``.

    The object exposes usage via ``response.usage`` with attributes:
      - ``prompt_tokens``
      - ``completion_tokens``
      - ``total_tokens``
    """
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        prompt     = getattr(usage, "prompt_tokens",     0) or 0
        completion = getattr(usage, "completion_tokens", 0) or 0
        total      = getattr(usage, "total_tokens",      None)
        if total is None:
            total = prompt + completion
        return ApiCallTokens(
            model=model,
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarise(calls: List[ApiCallTokens]) -> Dict[str, Any]:
    """
    Aggregate a list of :class:`ApiCallTokens` into a display-ready summary.

    Cache hits (``from_cache=True``) are counted separately and do not
    contribute to the token totals — no API call was made for them.

    Returns a dict ready to be JSON-serialised and sent to the UI.
    """
    real_calls  = [c for c in calls if not c.from_cache]
    cache_hits  = [c for c in calls if c.from_cache]

    return {
        "total_prompt_tokens":     sum(c.prompt_tokens     for c in real_calls),
        "total_completion_tokens": sum(c.completion_tokens for c in real_calls),
        "total_tokens":            sum(c.total_tokens      for c in real_calls),
        "api_calls":               len(real_calls),
        "cache_hits":              len(cache_hits),
        "calls":                   [c.to_dict() for c in calls],
    }
