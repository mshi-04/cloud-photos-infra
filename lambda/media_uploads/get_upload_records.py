import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def handler(event, context):
    identity_id = event["requestContext"]["identity"]["cognitoIdentityId"]
    if not identity_id:
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Unauthorized"}),
        }

    params = event.get("queryStringParameters") or {}
    limit = min(int(params.get("limit", 100)), 500)

    query_params = {
        "KeyConditionExpression": boto3.dynamodb.conditions.Key("userId").eq(identity_id),
        "Limit": limit,
    }

    last_key = params.get("lastEvaluatedKey")
    if last_key:
        query_params["ExclusiveStartKey"] = json.loads(last_key)

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
