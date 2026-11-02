import json

import pytest

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.errors import AuthorizationError, ValidationError
from cloud_photos.media_uploads.models import (
    CloudStoragePath,
    CreateUploadRecordRequest,
    FileSize,
    GetUploadRecordsRequest,
    MediaId,
    MediaType,
    PageCursor,
    PageLimit,
)

IDENTITY_ID = IdentityId("ap-northeast-1:test-user-id")
CLOUD_STORAGE_PATH = f"private/{IDENTITY_ID.value}/media-001.jpg"


class TestMediaId:
    def test_parse_strips_whitespace(self):
        assert MediaId.parse("  media-001  ") == MediaId("media-001")

    def test_parse_reports_missing_field(self):
        with pytest.raises(ValidationError, match=r"^Missing required field: mediaId$"):
            MediaId.parse(None)

    @pytest.mark.parametrize("raw", ["", "   ", 123, ["media-001"]])
    def test_parse_rejects_blank_or_non_string(self, raw):
        with pytest.raises(ValidationError, match=r"^mediaId must be a non-empty string$"):
            MediaId.parse(raw)

    def test_direct_construction_is_validated(self):
        with pytest.raises(ValidationError, match=r"^mediaId must be a non-empty string$"):
            MediaId("")


class TestCloudStoragePath:
    def test_parse_strips_whitespace(self):
        assert CloudStoragePath.parse(f"  {CLOUD_STORAGE_PATH}  ").value == CLOUD_STORAGE_PATH

    def test_direct_construction_is_validated(self):
        with pytest.raises(ValidationError, match=r"^cloudStoragePath must be a non-empty string$"):
            CloudStoragePath("")

    def test_belongs_to_owner(self):
        assert CloudStoragePath(CLOUD_STORAGE_PATH).belongs_to(IDENTITY_ID)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("private/other-user/media-001.jpg", id="other_user"),
            pytest.param(f"private/{IDENTITY_ID.value}", id="prefix_without_separator"),
            pytest.param(f"private/{IDENTITY_ID.value}-suffix/media-001.jpg", id="longer_identity"),
            pytest.param(f"public/{IDENTITY_ID.value}/media-001.jpg", id="not_private"),
        ],
    )
    def test_does_not_belong_to_owner(self, value):
        assert not CloudStoragePath(value).belongs_to(IDENTITY_ID)

    def test_text_hides_identity_in_path(self):
        path = CloudStoragePath(CLOUD_STORAGE_PATH)
        assert str(path) == "***"
        assert repr(path) == "CloudStoragePath(***)"


class TestMediaType:
    @pytest.mark.parametrize(
        ("raw", "expected"), [("IMAGE", MediaType.IMAGE), ("VIDEO", MediaType.VIDEO), (" VIDEO ", MediaType.VIDEO)]
    )
    def test_parse_accepts_known_types(self, raw, expected):
        assert MediaType.parse(raw) is expected

    def test_parse_reports_missing_field(self):
        with pytest.raises(ValidationError, match=r"^Missing required field: mediaType$"):
            MediaType.parse(None)

    @pytest.mark.parametrize("raw", ["GIF", "image", "", 123])
    def test_parse_rejects_unknown_type(self, raw):
        with pytest.raises(ValidationError, match=r"^mediaType must be IMAGE or VIDEO$"):
            MediaType.parse(raw)


class TestFileSize:
    @pytest.mark.parametrize(("raw", "expected"), [(0, 0), (12345, 12345), (100.0, 100)])
    def test_parse_accepts_whole_numbers(self, raw, expected):
        assert FileSize.parse(raw) == FileSize(expected)

    @pytest.mark.parametrize("raw", [True, "100", None, [1]])
    def test_parse_rejects_non_number(self, raw):
        with pytest.raises(ValidationError, match=r"^fileSize must be a number$"):
            FileSize.parse(raw)

    def test_parse_rejects_fraction(self):
        with pytest.raises(ValidationError, match=r"^fileSize must be an integer$"):
            FileSize.parse(1.5)

    def test_parse_rejects_negative(self):
        with pytest.raises(ValidationError, match=r"^fileSize must be non-negative$"):
            FileSize.parse(-1)

    def test_accepts_upper_limit(self):
        assert FileSize.parse(2**63 - 1) == FileSize(2**63 - 1)

    @pytest.mark.parametrize("raw", [2**63, 10**40, 1e300])
    def test_parse_rejects_value_over_upper_limit(self, raw):
        with pytest.raises(ValidationError, match=r"^fileSize must be at most 9223372036854775807$"):
            FileSize.parse(raw)

    @pytest.mark.parametrize("value", [True, 1.0])
    def test_direct_construction_requires_int(self, value):
        with pytest.raises(ValidationError, match=r"^fileSize must be an integer$"):
            FileSize(value)


class TestPageLimit:
    @pytest.mark.parametrize(("raw", "expected"), [("50", 50), (50, 50), ("9999", 500), ("0", 1), ("-5", 1)])
    def test_parse_clamps_to_range(self, raw, expected):
        assert PageLimit.parse(raw) == PageLimit(expected)

    @pytest.mark.parametrize("raw", ["abc", "", None, True, [1]])
    def test_parse_rejects_invalid_value(self, raw):
        with pytest.raises(ValidationError, match=r"^Invalid limit parameter$"):
            PageLimit.parse(raw)

    @pytest.mark.parametrize("value", [0, 501])
    def test_direct_construction_checks_range(self, value):
        with pytest.raises(ValidationError, match=r"^limit must be between 1 and 500$"):
            PageLimit(value)


class TestPageCursor:
    def test_parse_returns_cursor_for_caller(self):
        raw = json.dumps({"userId": IDENTITY_ID.value, "mediaId": " media-001 "})
        assert PageCursor.parse(raw, IDENTITY_ID) == PageCursor(IDENTITY_ID, MediaId("media-001"))

    def test_parse_rejects_other_users_key(self):
        raw = json.dumps({"userId": "other-user", "mediaId": "media-001"})
        with pytest.raises(AuthorizationError, match=r"^lastEvaluatedKey does not match your identity$"):
            PageCursor.parse(raw, IDENTITY_ID)

    @pytest.mark.parametrize("raw", ["not-json", 123])
    def test_parse_rejects_invalid_json(self, raw):
        with pytest.raises(ValidationError, match=r"^Invalid lastEvaluatedKey parameter$"):
            PageCursor.parse(raw, IDENTITY_ID)

    def test_parse_rejects_deeply_nested_json(self):
        depth = 100_000
        with pytest.raises(ValidationError, match=r"^Invalid lastEvaluatedKey parameter$"):
            PageCursor.parse("[" * depth + "]" * depth, IDENTITY_ID)

    def test_parse_rejects_non_object(self):
        with pytest.raises(ValidationError, match=r"^lastEvaluatedKey must be an object$"):
            PageCursor.parse(json.dumps([1, 2]), IDENTITY_ID)

    @pytest.mark.parametrize("media_id", [None, "  ", 123])
    def test_parse_rejects_blank_media_id(self, media_id):
        raw = json.dumps({"userId": IDENTITY_ID.value, "mediaId": media_id})
        with pytest.raises(ValidationError, match=r"^lastEvaluatedKey\.mediaId must be a non-empty string$"):
            PageCursor.parse(raw, IDENTITY_ID)


class TestCreateUploadRecordRequest:
    def _valid_data(self, **kwargs):
        data = {
            "mediaId": "media-001",
            "cloudStoragePath": CLOUD_STORAGE_PATH,
            "contentType": "image/jpeg",
            "mediaType": "IMAGE",
        }
        data.update(kwargs)
        return data

    def test_valid_minimal(self):
        req = CreateUploadRecordRequest.parse(self._valid_data())
        assert req.media_id == MediaId("media-001")
        assert req.cloud_storage_path == CloudStoragePath(CLOUD_STORAGE_PATH)
        assert req.content_type == "image/jpeg"
        assert req.media_type is MediaType.IMAGE
        assert req.file_size is None

    def test_valid_with_file_size(self):
        req = CreateUploadRecordRequest.parse(self._valid_data(fileSize=12345))
        assert req.file_size == FileSize(12345)

    def test_valid_file_size_float_integer(self):
        req = CreateUploadRecordRequest.parse(self._valid_data(fileSize=100.0))
        assert req.file_size == FileSize(100)

    def test_valid_media_type_video(self):
        req = CreateUploadRecordRequest.parse(self._valid_data(mediaType="VIDEO"))
        assert req.media_type is MediaType.VIDEO

    def test_strips_whitespace(self):
        req = CreateUploadRecordRequest.parse(self._valid_data(mediaId="  media-001  ", contentType=" image/jpeg "))
        assert req.media_id == MediaId("media-001")
        assert req.content_type == "image/jpeg"

    @pytest.mark.parametrize("field", ["mediaId", "cloudStoragePath", "contentType", "mediaType"])
    def test_missing_required_field(self, field):
        data = self._valid_data()
        del data[field]
        with pytest.raises(ValidationError, match=rf"^Missing required field: {field}$"):
            CreateUploadRecordRequest.parse(data)

    @pytest.mark.parametrize("field", ["mediaId", "cloudStoragePath", "contentType"])
    def test_blank_text_field(self, field):
        with pytest.raises(ValidationError, match=rf"^{field} must be a non-empty string$"):
            CreateUploadRecordRequest.parse(self._valid_data(**{field: "   "}))

    def test_reports_first_invalid_field(self):
        with pytest.raises(ValidationError, match=r"^mediaId must be a non-empty string$"):
            CreateUploadRecordRequest.parse(self._valid_data(mediaId="", mediaType="GIF"))

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"mediaType": "GIF"}, r"^mediaType must be IMAGE or VIDEO$"),
            ({"mediaType": 123}, r"^mediaType must be IMAGE or VIDEO$"),
            ({"fileSize": True}, r"^fileSize must be a number$"),
            ({"fileSize": "100"}, r"^fileSize must be a number$"),
            ({"fileSize": -1}, r"^fileSize must be non-negative$"),
            ({"fileSize": 1.5}, r"^fileSize must be an integer$"),
        ],
    )
    def test_invalid_value(self, kwargs, message):
        with pytest.raises(ValidationError, match=message):
            CreateUploadRecordRequest.parse(self._valid_data(**kwargs))

    @pytest.mark.parametrize("data", [[], "string", None])
    def test_data_not_object_rejected(self, data):
        with pytest.raises(ValidationError, match=r"^Request body must be an object$"):
            CreateUploadRecordRequest.parse(data)


class TestGetUploadRecordsRequest:
    @pytest.mark.parametrize("params", [{}, None, {"lastEvaluatedKey": ""}])
    def test_defaults(self, params):
        req = GetUploadRecordsRequest.parse(params, IDENTITY_ID)
        assert req.limit == PageLimit(100)
        assert req.cursor is None

    def test_custom_limit(self):
        req = GetUploadRecordsRequest.parse({"limit": "50"}, IDENTITY_ID)
        assert req.limit == PageLimit(50)

    @pytest.mark.parametrize(("raw", "expected"), [("0", 1), ("501", 500), ("9999", 500)])
    def test_limit_is_clamped(self, raw, expected):
        req = GetUploadRecordsRequest.parse({"limit": raw}, IDENTITY_ID)
        assert req.limit == PageLimit(expected)

    def test_invalid_limit(self):
        with pytest.raises(ValidationError, match="limit"):
            GetUploadRecordsRequest.parse({"limit": "abc"}, IDENTITY_ID)

    def test_valid_last_evaluated_key(self):
        key = json.dumps({"userId": IDENTITY_ID.value, "mediaId": "media-001"})
        req = GetUploadRecordsRequest.parse({"lastEvaluatedKey": key}, IDENTITY_ID)
        assert req.cursor == PageCursor(IDENTITY_ID, MediaId("media-001"))

    def test_last_evaluated_key_wrong_user(self):
        key = json.dumps({"userId": "other-user", "mediaId": "media-001"})
        with pytest.raises(AuthorizationError):
            GetUploadRecordsRequest.parse({"lastEvaluatedKey": key}, IDENTITY_ID)

    @pytest.mark.parametrize("params", ["string", [1, 2]])
    def test_params_not_dict_rejected(self, params):
        with pytest.raises(ValidationError, match=r"^params must be a dict$"):
            GetUploadRecordsRequest.parse(params, IDENTITY_ID)
