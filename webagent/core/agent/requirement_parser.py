"""
Parses a natural-language scraping requirement into structured data.

Returns a dict with:
  query  – the search term / product name
  sites  – list of target domains (e.g. ["amazon.in", "flipkart.com"])
  fields – list of field names to extract (e.g. ["price", "title"])
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """You are a web-scraping assistant.
Parse the user's scraping requirement and return ONLY a JSON object — no markdown, no explanation.

Schema:
{{
  "query":  "<product / search term>",
  "sites":  ["<domain1>", "<domain2>"],
  "fields": ["<field1>", "<field2>"]
}}

Rules:
- "query"  is the core product or topic to search for.
- "sites"  are the bare domains the user mentioned (e.g. "amazon.in", not "www.amazon.in").
- "fields" are snake_case field names derived from what the user wants.

Requirement:
{requirement}"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_requirement(
    requirement: str,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
    provider: str = "google",
) -> Dict[str, Any]:
    """Return parsed {query, sites, fields} from a natural-language requirement."""
    prompt = _PROMPT_TEMPLATE.format(requirement=requirement)
    try:
        raw = _call_ai(prompt, api_key, model_name, provider)
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        result = json.loads(raw)
        return {
            "query":  result.get("query", ""),
            "sites":  [s.lower().lstrip("www.") for s in result.get("sites", [])],
            "fields": result.get("fields", []),
        }
    except Exception as exc:
        logger.warning(f"AI parse failed [model={model_name}] ({exc}), using regex fallback")
        return _regex_fallback(requirement)


# ---------------------------------------------------------------------------
# AI backends
# ---------------------------------------------------------------------------

def _call_ai(prompt: str, api_key: Optional[str], model_name: str, provider: str) -> str:
    if provider == "google" or (model_name and model_name.startswith("gemini")):
        return _call_gemini(prompt, api_key, model_name)
    return _call_litellm(prompt, api_key, model_name)


def _call_gemini(prompt: str, api_key: Optional[str], model_name: str) -> str:
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise ValueError("No Gemini API key available")
    # Strip LiteLLM provider prefix: "gemini/gemini-2.0-flash" → "gemini-2.0-flash"
    clean_model = model_name.split("/")[-1]
    from google import genai  # type: ignore
    client = genai.Client(api_key=key)
    response = client.models.generate_content(model=clean_model, contents=prompt)
    return response.text


def _call_litellm(prompt: str, api_key: Optional[str], model_name: str) -> str:
    from litellm import completion  # type: ignore
    messages = [{"role": "user", "content": prompt}]
    resp = completion(model=model_name, messages=messages, api_key=api_key)
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# Regex fallback (no AI needed)
# ---------------------------------------------------------------------------

def _regex_fallback(requirement: str) -> Dict[str, Any]:
    req = requirement.lower()

    # Domains – anything that looks like domain.tld or domain.tld.cc
    sites = re.findall(r"\b(?:www\.)?([a-z0-9-]+\.[a-z]{2,3}(?:\.[a-z]{2})?)\b", req)
    # Filter out common false positives
    bad = {"e.g", "i.e", "etc", "com", "in", "net", "org"}
    sites = [s for s in sites if s not in bad]

    # Fields – words/phrases listed after "want", "need", "extract", "get", "including"
    field_match = re.search(
        r"(?:want|need|extract|get|including?)[:\s]+([\w ,_]+?)(?:\.|$)", req
    )
    if field_match:
        raw_fields = re.split(r"[,\s]+and\s+|,\s*", field_match.group(1))
        fields = [f.strip().replace(" ", "_") for f in raw_fields if f.strip()]
    else:
        fields = ["title", "price", "url"]

    # Query – text between "for" / "about" and "from" / "on" / end
    q_match = re.search(r"(?:for|about)\s+([\w\s]+?)(?:\s+from|\s+on|\s+at|\s+in\b|,|$)", req)
    query = q_match.group(1).strip() if q_match else ""

    return {"query": query, "sites": sites, "fields": fields}
