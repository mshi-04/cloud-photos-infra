import json
import os

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

    media_id = (event.get("pathParameters") or {}).get("mediaId")
    if not media_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing mediaId"}),
        }

    table.delete_item(
        Key={
            "userId": identity_id,
            "mediaId": media_id,
        }
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "deleted"}),
    }
