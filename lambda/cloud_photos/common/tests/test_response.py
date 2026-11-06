import json
from decimal import Decimal

import pytest

from cloud_photos.common.response import error, success


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

    def test_no_content_has_empty_body(self):
        resp = success(204)
        assert resp == {"statusCode": 204, "headers": {"Content-Type": "application/json"}, "body": ""}

    def test_explicit_none_has_empty_body(self):
        assert success(204, None)["body"] == ""

    @pytest.mark.parametrize("body", [{}, [], 0, False, ""])
    def test_falsy_body_is_json(self, body):
        assert json.loads(success(200, body)["body"]) == body

    def test_non_json_value_is_serialized_as_string(self):
        assert json.loads(success(200, {"amount": Decimal("1.5")})["body"]) == {"amount": "1.5"}


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
