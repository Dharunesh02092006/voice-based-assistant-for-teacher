"""
Defensive JSON parsing for LLM outputs.

Even when a model is asked for strict JSON in JSON mode, real-world output
occasionally arrives wrapped in markdown fences, with trailing commentary,
or with minor formatting noise. This module isolates and repairs the JSON
object before the rest of the app ever sees it, so a single malformed
response doesn't crash the Streamlit UI.
"""

from __future__ import annotations

import json
import re
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class JSONParseError(ValueError):
    """Raised when a model's output cannot be coerced into valid JSON."""


def safe_json_parse(raw_text: str) -> dict[str, Any]:
    """Best-effort parse of `raw_text` into a dict, tolerating common LLM
    formatting quirks (markdown fences, leading/trailing prose)."""
    if not raw_text or not raw_text.strip():
        raise JSONParseError("Empty response from model.")

    candidates = [raw_text.strip()]

    fence_match = _FENCE_RE.search(raw_text)
    if fence_match:
        candidates.insert(0, fence_match.group(1).strip())

    # Fallback: grab the largest {...} span in the text.
    first_brace = raw_text.find("{")
    last_brace = raw_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(raw_text[first_brace : last_brace + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    logger.error("Failed to parse JSON from model output: %.200s", raw_text)
    raise JSONParseError("Model did not return valid JSON.")
