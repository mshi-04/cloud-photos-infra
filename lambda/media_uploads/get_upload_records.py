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

    params = event.get("queryStringParameters") or {}

    try:
        limit = int(params.get("limit", 100))
        limit = max(1, min(limit, 500))
    except (ValueError, TypeError):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid limit parameter"}),
        }

    query_params = {
        "KeyConditionExpression": boto3.dynamodb.conditions.Key("userId").eq(identity_id),
        "Limit": limit,
    }

    last_key = params.get("lastEvaluatedKey")
    if last_key:
        try:
            query_params["ExclusiveStartKey"] = json.loads(last_key)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid lastEvaluatedKey parameter"}),
            }

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
