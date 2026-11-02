import json
from collections.abc import Mapping
from typing import Any


def parse_body(event: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the JSON object in the request body, or None when the body is not a JSON object."""
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(body, dict):
        return None
    return body
