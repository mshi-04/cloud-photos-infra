from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

from cloud_photos.common import masking
from cloud_photos.common.errors import ValidationError


def _get_identity_id(event: Mapping[str, Any]) -> str | None:
    """Return the Cognito Identity ID, or None when the request carries no usable one.

    API Gateway can send requestContext or identity as null, so missing, null and
    non-object values are all treated as unauthenticated instead of raising.
    """
    request_context = event.get("requestContext")
    if not isinstance(request_context, dict):
        return None
    identity = request_context.get("identity")
    if not isinstance(identity, dict):
        return None
    identity_id = identity.get("cognitoIdentityId")
    if not isinstance(identity_id, str) or not identity_id:
        return None
    return identity_id


def _mask_identity(identity_id: str | None) -> str:
    """Masks an identity ID, showing only the first 4 and last 4 characters for logging."""
    if not identity_id or len(identity_id) <= masking.FULLY_MASKED_MAX_LENGTH:
        return masking.MASK
    return f"{identity_id[:4]}{masking.MASK}{identity_id[-4:]}"


@dataclass(frozen=True, slots=True)
class IdentityId:
    """The caller's Cognito Identity ID. It masks itself when converted to text, so it is safe to log."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValidationError("identity id is required")

    @classmethod
    def from_event(cls, event: Mapping[str, Any]) -> Self | None:
        """Return the caller's Identity ID, or None when the request is unauthenticated."""
        identity_id = _get_identity_id(event)
        if identity_id is None:
            return None
        return cls(identity_id)

    def __str__(self) -> str:
        return _mask_identity(self.value)

    def __repr__(self) -> str:
        return f"IdentityId({_mask_identity(self.value)})"
