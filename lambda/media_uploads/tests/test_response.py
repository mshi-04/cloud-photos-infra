import json

from response import error, success


class TestSuccess:
    def test_status_code(self):
        resp = success(200, {"key": "value"})
        assert resp["statusCode"] == 200

    def test_body_is_json(self):
        resp = success(201, {"message": "created"})
        body = json.loads(resp["body"])
        assert body == {"message": "created"}

    def test_content_type_header(self):
        resp = success(200, {})
        assert resp["headers"]["Content-Type"] == "application/json"


class TestError:
    def test_status_code(self):
        resp = error(400, "Bad Request")
        assert resp["statusCode"] == 400

    def test_body_contains_message(self):
        resp = error(403, "Unauthorized")
        body = json.loads(resp["body"])
        assert body == {"message": "Unauthorized"}

    def test_content_type_header(self):
        resp = error(500, "Internal server error")
        assert resp["headers"]["Content-Type"] == "application/json"
