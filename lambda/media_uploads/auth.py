from typing import Any, Dict, Optional

def get_identity_id(event: Dict[str, Any]) -> Optional[str]:
    return (
        event.get("requestContext", {})
        .get("identity", {})
        .get("cognitoIdentityId")
    )

def mask_identity(identity_id: str) -> str:
    """Masks an identity ID, showing only the first 4 and last 4 characters for logging."""
    if not identity_id:
        return "***"
    return f"{identity_id[:4]}***{identity_id[-4:]}" if len(identity_id) > 8 else "***"
