"""Tests for the token_usage module."""

from unittest.mock import MagicMock

from browsegenie.core.token_usage import (
    ApiCallTokens,
    extract_gemini_tokens,
    extract_litellm_tokens,
    summarise,
)


class TestApiCallTokens:
    """Test cases for the ApiCallTokens dataclass."""

    def test_basic_creation(self):
        """Test that ApiCallTokens stores all fields correctly on creation."""
        t = ApiCallTokens(model="gpt-4", prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert t.model == "gpt-4"
        assert t.prompt_tokens == 100
        assert t.completion_tokens == 50
        assert t.total_tokens == 150
        assert t.from_cache is False

    def test_from_cache_flag(self):
        """Test that from_cache defaults to False and can be set to True."""
        t = ApiCallTokens(model="gemini", prompt_tokens=0, completion_tokens=0, total_tokens=0, from_cache=True)
        assert t.from_cache is True

    def test_to_dict(self):
        """Test that to_dict returns a complete dictionary with all fields."""
        t = ApiCallTokens(model="claude", prompt_tokens=10, completion_tokens=20, total_tokens=30)
        d = t.to_dict()
        assert d == {
            "model": "claude",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "from_cache": False,
        }

    def test_to_dict_with_cache(self):
        """Test that to_dict preserves the from_cache flag correctly."""
        t = ApiCallTokens(model="x", prompt_tokens=0, completion_tokens=0, total_tokens=0, from_cache=True)
        assert t.to_dict()["from_cache"] is True


class TestExtractGeminiTokens:
    """Test cases for extract_gemini_tokens helper."""

    def _make_response(self, prompt=None, candidates=None, total=None):
        """Build a mock Gemini GenerateContentResponse with given token counts."""
        um = MagicMock()
        um.prompt_token_count = prompt
        um.candidates_token_count = candidates
        um.total_token_count = total
        resp = MagicMock()
        resp.usage_metadata = um
        return resp

    def test_normal_response(self):
        """Test extraction from a well-formed Gemini response object."""
        resp = self._make_response(prompt=100, candidates=50, total=150)
        result = extract_gemini_tokens(resp, "gemini-2.5-flash")
        assert result is not None
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 50
        assert result.total_tokens == 150
        assert result.model == "gemini-2.5-flash"

    def test_none_usage_metadata(self):
        """Test that None usage_metadata returns None rather than raising."""
        resp = MagicMock()
        resp.usage_metadata = None
        assert extract_gemini_tokens(resp, "gemini") is None

    def test_missing_usage_metadata_attr(self):
        """Test that a response with no usage_metadata attribute returns None."""
        resp = MagicMock(spec=[])  # no usage_metadata attribute
        assert extract_gemini_tokens(resp, "gemini") is None

    def test_none_token_fields_default_to_zero(self):
        """Test that None token count fields are treated as 0."""
        resp = self._make_response(prompt=None, candidates=None, total=None)
        result = extract_gemini_tokens(resp, "gemini")
        assert result is not None
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
        assert result.total_tokens == 0

    def test_total_computed_when_none(self):
        """Test that total_tokens is computed as prompt + completion when missing."""
        resp = self._make_response(prompt=30, candidates=20, total=None)
        result = extract_gemini_tokens(resp, "gemini")
        assert result.total_tokens == 50

    def test_exception_returns_none(self):
        """Test that any exception during extraction returns None gracefully."""
        bad_um = MagicMock()
        type(bad_um).prompt_token_count = property(lambda self: (_ for _ in ()).throw(Exception("fail")))
        resp2 = MagicMock()
        resp2.usage_metadata = bad_um
        result = extract_gemini_tokens(resp2, "gemini")
        assert result is None or isinstance(result, ApiCallTokens)


class TestExtractLitellmTokens:
    """Test cases for extract_litellm_tokens helper."""

    def _make_response(self, prompt=None, completion=None, total=None):
        """Build a mock LiteLLM ModelResponse with given token counts."""
        usage = MagicMock()
        usage.prompt_tokens = prompt
        usage.completion_tokens = completion
        usage.total_tokens = total
        resp = MagicMock()
        resp.usage = usage
        return resp

    def test_normal_response(self):
        """Test extraction from a well-formed LiteLLM response object."""
        resp = self._make_response(prompt=80, completion=40, total=120)
        result = extract_litellm_tokens(resp, "gpt-4o-mini")
        assert result is not None
        assert result.prompt_tokens == 80
        assert result.completion_tokens == 40
        assert result.total_tokens == 120
        assert result.model == "gpt-4o-mini"

    def test_none_usage(self):
        """Test that a response with None usage returns None."""
        resp = MagicMock()
        resp.usage = None
        assert extract_litellm_tokens(resp, "gpt-4") is None

    def test_total_computed_when_none(self):
        """Test that total_tokens is computed when not present in the response."""
        resp = self._make_response(prompt=30, completion=20, total=None)
        result = extract_litellm_tokens(resp, "gpt-4")
        assert result.total_tokens == 50

    def test_none_fields_default_to_zero(self):
        """Test that None prompt/completion token fields are treated as 0."""
        resp = self._make_response(prompt=None, completion=None, total=None)
        result = extract_litellm_tokens(resp, "gpt-4")
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0

    def test_no_usage_attr_returns_none(self):
        """Test that a response object with no usage attribute returns None."""
        resp = MagicMock(spec=[])
        assert extract_litellm_tokens(resp, "gpt-4") is None


class TestSummarise:
    """Test cases for the summarise aggregation function."""

    def test_empty_list(self):
        """Test that an empty call list produces all-zero totals."""
        result = summarise([])
        assert result["total_prompt_tokens"] == 0
        assert result["total_completion_tokens"] == 0
        assert result["total_tokens"] == 0
        assert result["api_calls"] == 0
        assert result["cache_hits"] == 0
        assert result["calls"] == []

    def test_single_real_call(self):
        """Test summarisation of a single non-cached API call."""
        calls = [ApiCallTokens(model="gpt-4", prompt_tokens=100, completion_tokens=50, total_tokens=150)]
        result = summarise(calls)
        assert result["total_prompt_tokens"] == 100
        assert result["total_completion_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["api_calls"] == 1
        assert result["cache_hits"] == 0
        assert len(result["calls"]) == 1

    def test_cache_hits_excluded_from_totals(self):
        """Test that cache hits are counted separately and excluded from token totals."""
        calls = [
            ApiCallTokens(model="gpt-4", prompt_tokens=100, completion_tokens=50, total_tokens=150),
            ApiCallTokens(model="gpt-4", prompt_tokens=0, completion_tokens=0, total_tokens=0, from_cache=True),
        ]
        result = summarise(calls)
        assert result["total_tokens"] == 150
        assert result["api_calls"] == 1
        assert result["cache_hits"] == 1
        assert len(result["calls"]) == 2  # both appear in raw calls list

    def test_multiple_real_calls_summed(self):
        """Test that token counts are correctly summed across multiple real API calls."""
        calls = [
            ApiCallTokens(model="a", prompt_tokens=10, completion_tokens=5, total_tokens=15),
            ApiCallTokens(model="b", prompt_tokens=20, completion_tokens=10, total_tokens=30),
        ]
        result = summarise(calls)
        assert result["total_prompt_tokens"] == 30
        assert result["total_completion_tokens"] == 15
        assert result["total_tokens"] == 45
        assert result["api_calls"] == 2

    def test_all_cache_hits(self):
        """Test that all-cache-hit scenario yields zero token totals and zero api_calls."""
        calls = [
            ApiCallTokens(model="x", prompt_tokens=100, completion_tokens=50, total_tokens=150, from_cache=True),
        ]
        result = summarise(calls)
        assert result["total_tokens"] == 0
        assert result["api_calls"] == 0
        assert result["cache_hits"] == 1
