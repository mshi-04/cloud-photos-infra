import json
import os
import time

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def handler(event, _context):
    identity_id = (
        event.get("requestContext", {})
        .get("identity", {})
        .get("cognitoIdentityId")
    )
    if not identity_id:
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Unauthorized"}),
        }

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid JSON body"}),
        }

    required_fields = ["mediaId", "cloudStoragePath", "contentType", "mediaType"]
    for field in required_fields:
        if field not in body:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": f"Missing required field: {field}"}),
            }

    if not isinstance(body["mediaId"], str):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "mediaId must be a string"}),
        }

    if not isinstance(body["contentType"], str):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "contentType must be a string"}),
        }

    # IDOR prevention: verify cloudStoragePath belongs to the requester
    cloud_path = body["cloudStoragePath"]
    if not isinstance(cloud_path, str) or not cloud_path.startswith(f"private/{identity_id}/"):
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "cloudStoragePath does not match your identity"}),
        }

    if body["mediaType"] not in ("IMAGE", "VIDEO"):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "mediaType must be IMAGE or VIDEO"}),
        }

    item = {
        "userId": identity_id,
        "mediaId": body["mediaId"],
        "cloudStoragePath": cloud_path,
        "contentType": body["contentType"],
        "mediaType": body["mediaType"],
        "uploadedAt": int(time.time() * 1000),
    }

    if "fileSize" in body:
        if not isinstance(body["fileSize"], (int, float)):
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "fileSize must be a number"}),
            }
        item["fileSize"] = int(body["fileSize"])

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(userId) AND attribute_not_exists(mediaId)",
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Record already exists, skipped"}),
        }

    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "created"}),
    }
