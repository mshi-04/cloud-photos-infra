from http import HTTPStatus
from typing import Any, Dict

from auth import get_identity_id
from constants import FIELD_MEDIA_ID, FIELD_USER_ID
from db import deserialize_item, dynamodb_client, serialize_item, table_name
from models import GetUploadRecordsRequest, ValidationError
from response import error, success


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    identity_id = get_identity_id(event)
    if not identity_id:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    params = event.get("queryStringParameters") or {}

    try:
        request_data = GetUploadRecordsRequest.from_dict(params, identity_id)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))
    except ValueError as e:
        return error(HTTPStatus.FORBIDDEN, str(e))

    query_params: Dict[str, Any] = {
        "TableName": table_name,
        "KeyConditionExpression": f"{FIELD_USER_ID} = :user_id",
        "ExpressionAttributeValues": serialize_item({":user_id": identity_id}),
        "Limit": request_data.limit,
    }

    if request_data.last_evaluated_key_user_id and request_data.last_evaluated_key_media_id:
        query_params["ExclusiveStartKey"] = serialize_item(
            {
                FIELD_USER_ID: request_data.last_evaluated_key_user_id,
                FIELD_MEDIA_ID: request_data.last_evaluated_key_media_id,
            }
        )

    response = dynamodb_client.query(**query_params)

    # Deserialize the items returned by the client API
    items = [deserialize_item(item) for item in response.get("Items", [])]

    body: Dict[str, Any] = {
        "records": items,
    }

    if "LastEvaluatedKey" in response:
        # Deserialize the LastEvaluatedKey to return standard JSON types to the client
        body["lastEvaluatedKey"] = deserialize_item(response["LastEvaluatedKey"])

    return success(HTTPStatus.OK, body)
