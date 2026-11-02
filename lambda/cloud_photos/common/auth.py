from typing import Any, Dict, Optional


def get_identity_id(event: Dict[str, Any]) -> Optional[str]:
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


def mask_identity(identity_id: Optional[str]) -> str:
    """Masks an identity ID, showing only the first 4 and last 4 characters for logging."""
    if not identity_id:
        return "***"
    return f"{identity_id[:4]}***{identity_id[-4:]}" if len(identity_id) > 8 else "***"
