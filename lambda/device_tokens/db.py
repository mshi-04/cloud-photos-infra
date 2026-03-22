import os
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Dict

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

dynamodb_client = boto3.client("dynamodb")
_table_name = os.getenv("TABLE_NAME")
if not _table_name:
    raise RuntimeError("TABLE_NAME environment variable is not set")
table_name = _table_name

serializer = TypeSerializer()
deserializer = TypeDeserializer()


def serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: serializer.serialize(v) for k, v in item.items()}


def _convert_decimals(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == int(value) else float(value)
    if isinstance(value, Mapping):
        return {k: _convert_decimals(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_convert_decimals(v) for v in value]
    return value


def deserialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _convert_decimals(deserializer.deserialize(v)) for k, v in item.items()}
