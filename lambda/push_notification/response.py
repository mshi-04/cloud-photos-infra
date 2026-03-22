import json
from typing import Any, Dict

JSON_HEADERS = {"Content-Type": "application/json"}


def success(status_code: int, body: Any = None, default: Any = str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "statusCode": status_code,
        "headers": JSON_HEADERS,
    }
    if body is not None:
        result["body"] = json.dumps(body, default=default)
    return result


def error(status_code: int, message: str) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": JSON_HEADERS,
        "body": json.dumps({"message": message}),
    }
