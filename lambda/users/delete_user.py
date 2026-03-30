import logging
import os
import time
from typing import Any, Dict, List

import boto3

import auth
import constants
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


def _flush_s3_batch(s3, bucket: str, objects_to_delete: List[Dict[str, str]]) -> None:
    result = s3.delete_objects(Bucket=bucket, Delete={"Objects": objects_to_delete, "Quiet": True})
    errors = result.get("Errors")
    if errors:
        keys = [e.get("Key") for e in errors]
        raise RuntimeError(
            f"s3.delete_objects failed for bucket {bucket}: keys={keys}, errors={errors}"
        )


def _delete_s3_objects(identity_id: str) -> None:
    s3 = _get_s3()
    bucket = os.environ["S3_BUCKET_NAME"]
    prefix = f"private/{identity_id}/"

    objects_to_delete: List[Dict[str, str]] = []
    paginator = s3.get_paginator("list_object_versions")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for version in page.get("Versions", []):
            objects_to_delete.append({"Key": version["Key"], "VersionId": version["VersionId"]})
            if len(objects_to_delete) == 1000:
                _flush_s3_batch(s3, bucket, objects_to_delete)
                objects_to_delete = []
        for marker in page.get("DeleteMarkers", []):
            objects_to_delete.append({"Key": marker["Key"], "VersionId": marker["VersionId"]})
            if len(objects_to_delete) == 1000:
                _flush_s3_batch(s3, bucket, objects_to_delete)
                objects_to_delete = []

    if objects_to_delete:
        _flush_s3_batch(s3, bucket, objects_to_delete)


def _batch_delete_items(dynamodb, table_name: str, items: List[Dict], sort_key_name: str) -> None:
    for i in range(0, len(items), 25):
        chunk = items[i : i + 25]
        requests = [
            {
                "DeleteRequest": {
                    "Key": {
                        constants.FIELD_USER_ID: item[constants.FIELD_USER_ID],
                        sort_key_name: item[sort_key_name],
                    }
                }
            }
            for item in chunk
        ]
        unprocessed = {table_name: requests}
        max_retries = 5
        for attempt in range(max_retries + 1):
            result = dynamodb.batch_write_item(RequestItems=unprocessed)
            unprocessed = result.get("UnprocessedItems", {})
            if not unprocessed:
                break
            if attempt < max_retries:
                wait = 0.1 * (2**attempt)
                logger.warning(
                    "UnprocessedItems in %s, retrying in %.1fs (attempt %d/%d)",
                    table_name,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"batch_write_item still had UnprocessedItems after {max_retries} retries for table {table_name}"
                )


def _delete_dynamodb_records(table_name: str, identity_id: str, sort_key_name: str) -> None:
    dynamodb = _get_dynamodb()

    result = dynamodb.query(
        TableName=table_name,
        KeyConditionExpression=f"{constants.FIELD_USER_ID} = :uid",
        ExpressionAttributeValues={":uid": {"S": identity_id}},
        ProjectionExpression=f"{constants.FIELD_USER_ID}, {sort_key_name}",
    )
    _batch_delete_items(dynamodb, table_name, result.get("Items", []), sort_key_name)

    while "LastEvaluatedKey" in result:
        result = dynamodb.query(
            TableName=table_name,
            KeyConditionExpression=f"{constants.FIELD_USER_ID} = :uid",
            ExpressionAttributeValues={":uid": {"S": identity_id}},
            ProjectionExpression=f"{constants.FIELD_USER_ID}, {sort_key_name}",
            ExclusiveStartKey=result["LastEvaluatedKey"],
        )
        _batch_delete_items(dynamodb, table_name, result.get("Items", []), sort_key_name)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    identity_id = auth.get_identity_id(event)
    if not identity_id:
        return response.error(401, "Unauthorized")

    logger.info("Deleting user data for %s", auth.mask_identity(identity_id))

    upload_records_table = os.environ["UPLOAD_RECORDS_TABLE_NAME"]
    device_tokens_table = os.environ["DEVICE_TOKENS_TABLE_NAME"]

    failed_subsystems: List[str] = []

    try:
        _delete_s3_objects(identity_id)
    except Exception as e:
        logger.error("Failed to delete S3 objects for %s: %s", auth.mask_identity(identity_id), e)
        failed_subsystems.append("S3")

    try:
        _delete_dynamodb_records(upload_records_table, identity_id, constants.FIELD_MEDIA_ID)
    except Exception as e:
        logger.error("Failed to delete upload records for %s: %s", auth.mask_identity(identity_id), e)
        failed_subsystems.append("DynamoDB/upload_records")

    try:
        _delete_dynamodb_records(device_tokens_table, identity_id, constants.FIELD_DEVICE_TOKEN)
    except Exception as e:
        logger.error("Failed to delete device tokens for %s: %s", auth.mask_identity(identity_id), e)
        failed_subsystems.append("DynamoDB/device_tokens")

    if failed_subsystems:
        return response.error(500, f"Failed to delete data from: {', '.join(failed_subsystems)}")

    return response.success(200, {"message": "User data deleted"})
