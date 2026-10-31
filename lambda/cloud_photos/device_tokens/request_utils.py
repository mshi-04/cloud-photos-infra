import json
from typing import Any, Dict, Optional


def parse_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(body, dict):
        return None
    return body
