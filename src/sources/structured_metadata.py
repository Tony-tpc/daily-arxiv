"""Shared normalization helpers for structured source metadata."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


def parse_json_object(value: Any) -> Dict[str, Any]:
    """Parse an object from plain or fenced LLM JSON output."""
    text = str(value or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Structured extraction response must be a JSON object")
    return parsed


def string_list(value: Any) -> List[str]:
    """Normalize a string or list into non-empty strings."""
    if isinstance(value, str):
        values = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        values = [str(part).strip() for part in value]
    else:
        values = []
    return [part for part in values if part]


def unique(values: List[str]) -> List[str]:
    """Preserve the first occurrence of every non-empty string."""
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def clean_optional(value: Any) -> Optional[str]:
    """Return a stripped string or None."""
    cleaned = str(value or "").strip()
    return cleaned or None
