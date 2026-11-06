from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

_serializer = TypeSerializer()
_deserializer = TypeDeserializer()


def serialize_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {k: _serializer.serialize(v) for k, v in item.items()}


def _convert_decimals(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == int(value) else float(value)
    if isinstance(value, Mapping):
        return {k: _convert_decimals(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_convert_decimals(v) for v in value]
    return value


def deserialize_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {k: _convert_decimals(_deserializer.deserialize(v)) for k, v in item.items()}
