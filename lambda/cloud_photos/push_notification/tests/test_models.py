import pytest

from cloud_photos.common.errors import ValidationError
from cloud_photos.push_notification.models import SuccessCount


class TestSuccessCount:
    @pytest.mark.parametrize("raw", [0, 1, 25])
    def test_parse_accepts_non_negative_integers(self, raw):
        assert SuccessCount.parse(raw).value == raw

    @pytest.mark.parametrize("raw", [-1, True, False, 1.5, 2.0, None, "five", "3"])
    def test_parse_rejects_other_values(self, raw):
        with pytest.raises(ValidationError, match=r"^successCount must be a non-negative integer$"):
            SuccessCount.parse(raw)

    @pytest.mark.parametrize("value", [-1, True])
    def test_direct_construction_is_validated(self, value):
        with pytest.raises(ValidationError):
            SuccessCount(value)

    def test_is_zero(self):
        assert SuccessCount(0).is_zero
        assert not SuccessCount(1).is_zero
