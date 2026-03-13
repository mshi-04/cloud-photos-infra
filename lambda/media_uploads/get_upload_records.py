import json
import os

import boto3
from boto3.dynamodb.conditions import Key

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
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Unauthorized"}),
        }

    params = event.get("queryStringParameters") or {}

    try:
        limit = int(params.get("limit", 100))
        limit = max(1, min(limit, 500))
    except (ValueError, TypeError):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Invalid limit parameter"}),
        }

    query_params = {
        "KeyConditionExpression": Key("userId").eq(identity_id),
        "Limit": limit,
    }

    last_key = params.get("lastEvaluatedKey")
    if last_key:
        try:
            exclusive_start_key = json.loads(last_key)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "Invalid lastEvaluatedKey parameter"}),
            }

        if not isinstance(exclusive_start_key, dict):
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "lastEvaluatedKey must be an object"}),
            }

        if exclusive_start_key.get("userId") != identity_id:
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "lastEvaluatedKey does not match your identity"}),
            }

        media_id_key = exclusive_start_key.get("mediaId")
        if not isinstance(media_id_key, str) or not media_id_key:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "lastEvaluatedKey.mediaId must be a non-empty string"}),
            }

        query_params["ExclusiveStartKey"] = exclusive_start_key

    response = table.query(**query_params)

    body = {
        "records": response["Items"],
    }
    if "LastEvaluatedKey" in response:
        body["lastEvaluatedKey"] = response["LastEvaluatedKey"]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }
