import json

from moto import mock_aws

from create_upload_record import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"
MEDIA_ID = "media-001"
CLOUD_STORAGE_PATH = f"private/{IDENTITY_ID}/{MEDIA_ID}.jpg"


def _make_event(body=None, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "body": json.dumps(body) if body is not None else None,
    }


def _valid_body(**kwargs):
    data = {
        "mediaId": MEDIA_ID,
        "cloudStoragePath": CLOUD_STORAGE_PATH,
        "contentType": "image/jpeg",
        "mediaType": "IMAGE",
    }
    data.update(kwargs)
    return data


@mock_aws
class TestCreateUploadRecord:
    def test_create_success(self, dynamodb_table):
        event = _make_event(_valid_body())
        resp = handler(event, None)
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["message"] == "created"
        assert "uploadedAt" in body

    def test_duplicate_skipped(self, dynamodb_table):
        event = _make_event(_valid_body())
        handler(event, None)
        resp = handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "skipped" in body["message"]

    def test_unauthorized_no_identity(self, dynamodb_table):
        event = {"requestContext": {"identity": {}}, "body": json.dumps(_valid_body())}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    def test_idor_prevention(self, dynamodb_table):
        body = _valid_body(cloudStoragePath="private/other-user/evil.jpg")
        resp = handler(_make_event(body), None)
        assert resp["statusCode"] == 403

    def test_invalid_json_body(self, dynamodb_table):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "body": "not-json",
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    def test_missing_media_id(self, dynamodb_table):
        body = _valid_body()
        del body["mediaId"]
        resp = handler(_make_event(body), None)
        assert resp["statusCode"] == 400

    def test_invalid_media_type(self, dynamodb_table):
        resp = handler(_make_event(_valid_body(mediaType="GIF")), None)
        assert resp["statusCode"] == 400

    def test_with_file_size(self, dynamodb_table):
        resp = handler(_make_event(_valid_body(fileSize=512000)), None)
        assert resp["statusCode"] == 201
