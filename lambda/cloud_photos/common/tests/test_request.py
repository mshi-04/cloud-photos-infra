import pytest

from cloud_photos.common.request import parse_body


class TestParseBody:
    @pytest.mark.parametrize(
        "body",
        ['{"key": "value", "nested": {"enabled": true}}', b'{"key": "value", "nested": {"enabled": true}}'],
    )
    def test_returns_json_object(self, body):
        assert parse_body({"body": body}) == {"key": "value", "nested": {"enabled": True}}

    @pytest.mark.parametrize("event", [{}, {"body": None}, {"body": ""}])
    def test_missing_or_empty_body_returns_empty_object(self, event):
        assert parse_body(event) == {}

    @pytest.mark.parametrize("body", ["{", '{"key":}', "not-json"])
    def test_malformed_json_returns_none(self, body):
        assert parse_body({"body": body}) is None

    @pytest.mark.parametrize("body", ["null", "[]", '"text"', "123", "true", "false"])
    def test_json_non_object_returns_none(self, body):
        assert parse_body({"body": body}) is None

    @pytest.mark.parametrize("body", [123, True, {"key": "value"}, ["value"]])
    def test_invalid_body_type_returns_none(self, body):
        assert parse_body({"body": body}) is None

    @pytest.mark.parametrize("body", [False, 0, [], {}])
    def test_falsy_non_string_body_returns_empty_object(self, body):
        assert parse_body({"body": body}) == {}
