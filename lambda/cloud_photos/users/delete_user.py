from __future__ import annotations

import functools
import itertools
import logging
import os
import time
from collections.abc import Callable, Mapping, Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import boto3

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.dynamodb import serialize_item
from cloud_photos.common.response import error, success
from cloud_photos.common.storage import PRIVATE_PATH_PREFIX
from cloud_photos.common.tables import FIELD_DEVICE_TOKEN, FIELD_MEDIA_ID, FIELD_USER_ID
from cloud_photos.users.constants import (
    BATCH_WRITE_BASE_WAIT_SECONDS,
    DYNAMODB_BATCH_WRITE_SIZE,
    MAX_BATCH_WRITE_RETRIES,
    S3_DELETE_BATCH_SIZE,
    SUBSYSTEM_DEVICE_TOKENS,
    SUBSYSTEM_S3,
    SUBSYSTEM_UPLOAD_RECORDS,
)

if TYPE_CHECKING:
    # The stubs are a development dependency; the Lambda runtime never imports them.
    from mypy_boto3_dynamodb import DynamoDBClient
    from mypy_boto3_dynamodb.type_defs import AttributeValueTypeDef, WriteRequestTypeDef
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import DeleteMarkerEntryTypeDef, ObjectIdentifierTypeDef, ObjectVersionTypeDef

logger = logging.getLogger(__name__)
# The deletion of a user's data is recorded even when the runtime's default level is WARNING.
logger.setLevel(logging.INFO)


@functools.cache
def get_s3_client() -> S3Client:
    return boto3.client("s3")


@functools.cache
def get_dynamodb_client() -> DynamoDBClient:
    return boto3.client("dynamodb")


def _flush_s3_batch(s3: S3Client, bucket: str, objects_to_delete: list[ObjectIdentifierTypeDef]) -> None:
    result = s3.delete_objects(Bucket=bucket, Delete={"Objects": objects_to_delete, "Quiet": True})
    errors = result.get("Errors")
    if errors:
        codes = [e.get("Code") for e in errors]
        raise RuntimeError(f"s3.delete_objects failed for bucket {bucket}: {len(errors)} object(s) failed, error_codes={codes}")


def _object_identifier(entry: ObjectVersionTypeDef | DeleteMarkerEntryTypeDef) -> ObjectIdentifierTypeDef | None:
    """Return the identifier that deletes this version, or None for an entry without a key."""
    key = entry.get("Key")
    if key is None:
        return None
    version_id = entry.get("VersionId")
    if version_id is None:
        return {"Key": key}
    return {"Key": key, "VersionId": version_id}


def _delete_s3_objects(bucket: str, identity_id: IdentityId) -> None:
    """Delete every version and delete marker under the user's private prefix."""
    s3 = get_s3_client()
    prefix = f"{PRIVATE_PATH_PREFIX}{identity_id.value}/"

    objects_to_delete: list[ObjectIdentifierTypeDef] = []
    for page in s3.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=prefix):
        for entry in itertools.chain(page.get("Versions", []), page.get("DeleteMarkers", [])):
            identifier = _object_identifier(entry)
            if identifier is None:
                continue
            objects_to_delete.append(identifier)
            if len(objects_to_delete) == S3_DELETE_BATCH_SIZE:
                _flush_s3_batch(s3, bucket, objects_to_delete)
                objects_to_delete = []

    if objects_to_delete:
        _flush_s3_batch(s3, bucket, objects_to_delete)


def _write_with_retries(dynamodb: DynamoDBClient, table_name: str, requests: Sequence[WriteRequestTypeDef]) -> None:
    """Run batch_write_item, retrying UnprocessedItems with exponential backoff."""
    unprocessed: Mapping[str, Sequence[Any]] = {table_name: requests}
    for attempt in range(MAX_BATCH_WRITE_RETRIES + 1):
        result = dynamodb.batch_write_item(RequestItems=unprocessed)
        unprocessed = result.get("UnprocessedItems", {})
        if not unprocessed:
            return
        if attempt == MAX_BATCH_WRITE_RETRIES:
            break
        wait = BATCH_WRITE_BASE_WAIT_SECONDS * (2**attempt)
        logger.warning(
            "UnprocessedItems in %s, retrying in %.1fs (attempt %d/%d)",
            table_name,
            wait,
            attempt + 1,
            MAX_BATCH_WRITE_RETRIES,
        )
        time.sleep(wait)
    raise RuntimeError(
        f"batch_write_item still had UnprocessedItems after {MAX_BATCH_WRITE_RETRIES} retries for table {table_name}"
    )


def _batch_delete_items(
    dynamodb: DynamoDBClient,
    table_name: str,
    items: Sequence[Mapping[str, AttributeValueTypeDef]],
    sort_key_name: str,
) -> None:
    for start in range(0, len(items), DYNAMODB_BATCH_WRITE_SIZE):
        chunk = items[start : start + DYNAMODB_BATCH_WRITE_SIZE]
        requests: list[WriteRequestTypeDef] = [
            {"DeleteRequest": {"Key": {FIELD_USER_ID: item[FIELD_USER_ID], sort_key_name: item[sort_key_name]}}} for item in chunk
        ]
        _write_with_retries(dynamodb, table_name, requests)


def _delete_dynamodb_records(table_name: str, identity_id: IdentityId, sort_key_name: str) -> None:
    """Delete every item of the user in the table, following LastEvaluatedKey across pages."""
    dynamodb = get_dynamodb_client()
    params: dict[str, Any] = {
        "TableName": table_name,
        "KeyConditionExpression": f"{FIELD_USER_ID} = :uid",
        "ExpressionAttributeValues": serialize_item({":uid": identity_id.value}),
        "ProjectionExpression": f"{FIELD_USER_ID}, {sort_key_name}",
    }
    while True:
        result = dynamodb.query(**params)
        _batch_delete_items(dynamodb, table_name, result.get("Items", []), sort_key_name)
        last_evaluated_key = result.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            return
        params = {**params, "ExclusiveStartKey": last_evaluated_key}


def _try_delete(subsystem: str, identity_id: IdentityId, delete: Callable[[], None]) -> bool:
    """Run one store's deletion and return whether it succeeded."""
    try:
        delete()
    except Exception:
        # Each store is deleted independently, so that a failure in one does not keep the user's data in the others.
        logger.exception("Failed to delete %s data for %s", subsystem, identity_id)
        return False
    return True


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.UNAUTHORIZED, "Unauthorized")

    # Read the whole configuration first, so that a missing variable stops the request before anything is deleted.
    bucket = os.environ["S3_BUCKET_NAME"]
    upload_records_table = os.environ["UPLOAD_RECORDS_TABLE_NAME"]
    device_tokens_table = os.environ["DEVICE_TOKENS_TABLE_NAME"]

    logger.info("Deleting user data for %s", identity_id)

    deletions: list[tuple[str, Callable[[], None]]] = [
        (SUBSYSTEM_S3, functools.partial(_delete_s3_objects, bucket, identity_id)),
        (
            SUBSYSTEM_UPLOAD_RECORDS,
            functools.partial(_delete_dynamodb_records, upload_records_table, identity_id, FIELD_MEDIA_ID),
        ),
        (
            SUBSYSTEM_DEVICE_TOKENS,
            functools.partial(_delete_dynamodb_records, device_tokens_table, identity_id, FIELD_DEVICE_TOKEN),
        ),
    ]
    failed_subsystems = [subsystem for subsystem, delete in deletions if not _try_delete(subsystem, identity_id, delete)]

    if failed_subsystems:
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Failed to delete data from: {', '.join(failed_subsystems)}")
    return success(HTTPStatus.OK, {"message": "User data deleted"})
