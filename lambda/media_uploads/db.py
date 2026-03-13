import os
from typing import Any, Dict

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

dynamodb_client = boto3.client("dynamodb")
table_name = os.environ["TABLE_NAME"]

serializer = TypeSerializer()
deserializer = TypeDeserializer()

def serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: serializer.serialize(v) for k, v in item.items()}

def deserialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: deserializer.deserialize(v) for k, v in item.items()}
