import logging
import os
from typing import Any, Dict, List

import boto3

import auth
import response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_s3 = None
_dynamodb = None


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.client("dynamodb")
    return _dynamodb


def _reset_for_testing():
    global _s3, _dynamodb
    _s3 = None
    _dynamodb = None


def _delete_s3_objects(identity_id: str) -> None:
    s3 = _get_s3()
    bucket = os.environ["S3_BUCKET_NAME"]
    prefix = f"private/{identity_id}/"

    objects_to_delete: List[Dict[str, str]] = []
    paginator = s3.get_paginator("list_object_versions")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for version in page.get("Versions", []):
            objects_to_delete.append({"Key": version["Key"], "VersionId": version["VersionId"]})
        for marker in page.get("DeleteMarkers", []):
            objects_to_delete.append({"Key": marker["Key"], "VersionId": marker["VersionId"]})

    for i in range(0, len(objects_to_delete), 1000):
        chunk = objects_to_delete[i : i + 1000]
        s3.delete_objects(Bucket=bucket, Delete={"Objects": chunk, "Quiet": True})


def _delete_dynamodb_records(table_name: str, identity_id: str, sort_key_name: str) -> None:
    dynamodb = _get_dynamodb()

    result = dynamodb.query(
        TableName=table_name,
        KeyConditionExpression="userId = :uid",
        ExpressionAttributeValues={":uid": {"S": identity_id}},
        ProjectionExpression=f"userId, {sort_key_name}",
    )
    items = result.get("Items", [])

    while "LastEvaluatedKey" in result:
        result = dynamodb.query(
            TableName=table_name,
            KeyConditionExpression="userId = :uid",
            ExpressionAttributeValues={":uid": {"S": identity_id}},
            ProjectionExpression=f"userId, {sort_key_name}",
            ExclusiveStartKey=result["LastEvaluatedKey"],
        )
        items.extend(result.get("Items", []))

    for i in range(0, len(items), 25):
        chunk = items[i : i + 25]
        requests = [
            {
                "DeleteRequest": {
                    "Key": {
                        "userId": item["userId"],
                        sort_key_name: item[sort_key_name],
                    }
                }
            }
            for item in chunk
        ]
        dynamodb.batch_write_item(RequestItems={table_name: requests})


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    identity_id = auth.get_identity_id(event)
    if not identity_id:
        return response.error(401, "Unauthorized")

    logger.info("Deleting user data for %s", auth.mask_identity(identity_id))

    upload_records_table = os.environ["UPLOAD_RECORDS_TABLE_NAME"]
    device_tokens_table = os.environ["DEVICE_TOKENS_TABLE_NAME"]

    try:
        _delete_s3_objects(identity_id)
    except Exception as e:
        logger.error("Failed to delete S3 objects: %s", e)

    try:
        _delete_dynamodb_records(upload_records_table, identity_id, "mediaId")
    except Exception as e:
        logger.error("Failed to delete upload records: %s", e)

    try:
        _delete_dynamodb_records(device_tokens_table, identity_id, "deviceToken")
    except Exception as e:
        logger.error("Failed to delete device tokens: %s", e)

    return response.success(200, {"message": "User data deleted"})
