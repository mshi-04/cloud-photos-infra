from typing import Any, Dict, Optional

def get_identity_id(event: Dict[str, Any]) -> Optional[str]:
    return (
        event.get("requestContext", {})
        .get("identity", {})
        .get("cognitoIdentityId")
    )
