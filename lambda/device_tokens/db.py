import os
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Dict

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

_dynamodb_client = None
_table_name = None

serializer = TypeSerializer()
deserializer = TypeDeserializer()


def get_dynamodb_client():
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = boto3.client("dynamodb")
    return _dynamodb_client


def get_table_name() -> str:
    global _table_name
    if _table_name is None:
        _table_name = os.environ["TABLE_NAME"]
    return _table_name


def _reset_for_testing():
    global _dynamodb_client, _table_name
    _dynamodb_client = None
    _table_name = None


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
