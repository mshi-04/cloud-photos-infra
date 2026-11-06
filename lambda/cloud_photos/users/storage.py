import functools
import itertools
from typing import TYPE_CHECKING

import boto3

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.storage import PRIVATE_PATH_PREFIX
from cloud_photos.users.constants import S3_DELETE_BATCH_SIZE

if TYPE_CHECKING:
    # The stubs are a development dependency; the Lambda runtime never imports them.
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import DeleteMarkerEntryTypeDef, ObjectIdentifierTypeDef, ObjectVersionTypeDef


@functools.cache
def get_s3_client() -> "S3Client":
    return boto3.client("s3")


def _flush_s3_batch(s3: "S3Client", bucket: str, objects_to_delete: list["ObjectIdentifierTypeDef"]) -> None:
    result = s3.delete_objects(Bucket=bucket, Delete={"Objects": objects_to_delete, "Quiet": True})
    errors = result.get("Errors")
    if errors:
        codes = [e.get("Code") for e in errors]
        raise RuntimeError(f"s3.delete_objects failed for bucket {bucket}: {len(errors)} object(s) failed, error_codes={codes}")


def _object_identifier(entry: "ObjectVersionTypeDef | DeleteMarkerEntryTypeDef") -> "ObjectIdentifierTypeDef | None":
    """Return the identifier that deletes this version, or None for an entry without a key."""
    key = entry.get("Key")
    if key is None:
        return None
    version_id = entry.get("VersionId")
    if version_id is None:
        return {"Key": key}
    return {"Key": key, "VersionId": version_id}


def delete_s3_objects(bucket: str, identity_id: IdentityId) -> None:
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
