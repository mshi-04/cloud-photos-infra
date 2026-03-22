from decimal import Decimal

import pytest
from db import _convert_decimals, deserialize_item, serialize_item


class TestSerializeItem:
    def test_serializes_string(self):
        result = serialize_item({"key": "value"})
        assert result == {"key": {"S": "value"}}

    def test_serializes_number(self):
        result = serialize_item({"count": 42})
        assert result == {"count": {"N": "42"}}

    def test_serializes_multiple_fields(self):
        result = serialize_item({"userId": "u1", "mediaId": "m1"})
        assert result["userId"] == {"S": "u1"}
        assert result["mediaId"] == {"S": "m1"}


class TestConvertDecimals:
    def test_integer_decimal(self):
        assert _convert_decimals(Decimal("10")) == 10
        assert isinstance(_convert_decimals(Decimal("10")), int)

    def test_float_decimal(self):
        assert _convert_decimals(Decimal("10.5")) == 10.5
        assert isinstance(_convert_decimals(Decimal("10.5")), float)

    def test_nested_dict(self):
        result = _convert_decimals({"a": Decimal("1"), "b": "str"})
        assert result == {"a": 1, "b": "str"}

    def test_list(self):
        result = _convert_decimals([Decimal("1"), Decimal("2.5")])
        assert result == [1, 2.5]

    def test_plain_value_passthrough(self):
        assert _convert_decimals("hello") == "hello"
        assert _convert_decimals(None) is None


class TestDeserializeItem:
    def test_deserializes_string(self):
        result = deserialize_item({"userId": {"S": "user-1"}})
        assert result == {"userId": "user-1"}

    def test_deserializes_number_as_int(self):
        result = deserialize_item({"uploadedAt": {"N": "1700000000000"}})
        assert result == {"uploadedAt": 1700000000000}
        assert isinstance(result["uploadedAt"], int)

    def test_deserializes_bool(self):
        result = deserialize_item({"isDeleted": {"BOOL": True}})
        assert result == {"isDeleted": True}
