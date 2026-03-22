import json

import pytest
from models import AuthorizationError, CreateUploadRecordRequest, GetUploadRecordsRequest, ValidationError

IDENTITY_ID = "ap-northeast-1:test-user-id"


class TestCreateUploadRecordRequest:
    def _valid_data(self, **kwargs):
        data = {
            "mediaId": "media-001",
            "cloudStoragePath": f"private/{IDENTITY_ID}/media-001.jpg",
            "contentType": "image/jpeg",
            "mediaType": "IMAGE",
        }
        data.update(kwargs)
        return data

    def test_valid_minimal(self):
        req = CreateUploadRecordRequest.from_dict(self._valid_data())
        assert req.media_id == "media-001"
        assert req.cloud_storage_path == f"private/{IDENTITY_ID}/media-001.jpg"
        assert req.content_type == "image/jpeg"
        assert req.media_type == "IMAGE"
        assert req.file_size is None

    def test_valid_with_file_size(self):
        req = CreateUploadRecordRequest.from_dict(self._valid_data(fileSize=12345))
        assert req.file_size == 12345

    def test_valid_file_size_float_integer(self):
        req = CreateUploadRecordRequest.from_dict(self._valid_data(fileSize=100.0))
        assert req.file_size == 100

    def test_valid_media_type_video(self):
        req = CreateUploadRecordRequest.from_dict(self._valid_data(mediaType="VIDEO"))
        assert req.media_type == "VIDEO"

    def test_strips_whitespace(self):
        req = CreateUploadRecordRequest.from_dict(self._valid_data(mediaId="  media-001  "))
        assert req.media_id == "media-001"

    def test_missing_media_id(self):
        data = self._valid_data()
        del data["mediaId"]
        with pytest.raises(ValidationError, match="mediaId"):
            CreateUploadRecordRequest.from_dict(data)

    def test_empty_media_id(self):
        with pytest.raises(ValidationError, match="mediaId"):
            CreateUploadRecordRequest.from_dict(self._valid_data(mediaId="   "))

    def test_missing_cloud_storage_path(self):
        data = self._valid_data()
        del data["cloudStoragePath"]
        with pytest.raises(ValidationError, match="cloudStoragePath"):
            CreateUploadRecordRequest.from_dict(data)

    def test_missing_content_type(self):
        data = self._valid_data()
        del data["contentType"]
        with pytest.raises(ValidationError, match="contentType"):
            CreateUploadRecordRequest.from_dict(data)

    def test_missing_media_type(self):
        data = self._valid_data()
        del data["mediaType"]
        with pytest.raises(ValidationError, match="mediaType"):
            CreateUploadRecordRequest.from_dict(data)

    def test_invalid_media_type(self):
        with pytest.raises(ValidationError, match="IMAGE or VIDEO"):
            CreateUploadRecordRequest.from_dict(self._valid_data(mediaType="GIF"))

    def test_file_size_bool_rejected(self):
        with pytest.raises(ValidationError, match="fileSize"):
            CreateUploadRecordRequest.from_dict(self._valid_data(fileSize=True))

    def test_file_size_negative_rejected(self):
        with pytest.raises(ValidationError, match="fileSize"):
            CreateUploadRecordRequest.from_dict(self._valid_data(fileSize=-1))

    def test_file_size_float_non_integer_rejected(self):
        with pytest.raises(ValidationError, match="fileSize"):
            CreateUploadRecordRequest.from_dict(self._valid_data(fileSize=1.5))


class TestGetUploadRecordsRequest:
    def test_defaults(self):
        req = GetUploadRecordsRequest.from_dict({}, IDENTITY_ID)
        assert req.limit == 100
        assert req.last_evaluated_key_user_id is None
        assert req.last_evaluated_key_media_id is None

    def test_defaults_with_none_params(self):
        req = GetUploadRecordsRequest.from_dict(None, IDENTITY_ID)
        assert req.limit == 100
        assert req.last_evaluated_key_user_id is None
        assert req.last_evaluated_key_media_id is None

    def test_custom_limit(self):
        req = GetUploadRecordsRequest.from_dict({"limit": "50"}, IDENTITY_ID)
        assert req.limit == 50

    def test_limit_clamped_to_max(self):
        req = GetUploadRecordsRequest.from_dict({"limit": "9999"}, IDENTITY_ID)
        assert req.limit == 500

    def test_limit_clamped_to_min(self):
        req = GetUploadRecordsRequest.from_dict({"limit": "0"}, IDENTITY_ID)
        assert req.limit == 1

    def test_invalid_limit(self):
        with pytest.raises(ValidationError, match="limit"):
            GetUploadRecordsRequest.from_dict({"limit": "abc"}, IDENTITY_ID)

    def test_bool_limit_rejected(self):
        with pytest.raises(ValidationError, match="limit"):
            GetUploadRecordsRequest.from_dict({"limit": True}, IDENTITY_ID)

    def test_valid_last_evaluated_key(self):
        key = json.dumps({"userId": IDENTITY_ID, "mediaId": "media-001"})
        req = GetUploadRecordsRequest.from_dict({"lastEvaluatedKey": key}, IDENTITY_ID)
        assert req.last_evaluated_key_user_id == IDENTITY_ID
        assert req.last_evaluated_key_media_id == "media-001"

    def test_last_evaluated_key_wrong_user(self):
        key = json.dumps({"userId": "other-user", "mediaId": "media-001"})
        with pytest.raises(AuthorizationError):
            GetUploadRecordsRequest.from_dict({"lastEvaluatedKey": key}, IDENTITY_ID)

    def test_last_evaluated_key_invalid_json(self):
        with pytest.raises(ValidationError, match="lastEvaluatedKey"):
            GetUploadRecordsRequest.from_dict({"lastEvaluatedKey": "not-json"}, IDENTITY_ID)

    def test_last_evaluated_key_not_object(self):
        with pytest.raises(ValidationError, match="lastEvaluatedKey"):
            GetUploadRecordsRequest.from_dict({"lastEvaluatedKey": json.dumps([1, 2])}, IDENTITY_ID)

    def test_last_evaluated_key_empty_media_id(self):
        key = json.dumps({"userId": IDENTITY_ID, "mediaId": "  "})
        with pytest.raises(ValidationError, match="mediaId"):
            GetUploadRecordsRequest.from_dict({"lastEvaluatedKey": key}, IDENTITY_ID)
