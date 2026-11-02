import json
from collections.abc import Callable
from typing import Any, Final

JSON_HEADERS: Final = {"Content-Type": "application/json"}


def success(status_code: int, body: Any = None, default: Callable[[Any], Any] = str) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": JSON_HEADERS,
        "body": json.dumps(body, default=default) if body is not None else "",
    }


def error(status_code: int, message: str) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": JSON_HEADERS,
        "body": json.dumps({"message": message}),
    }
