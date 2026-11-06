class ValidationError(ValueError):
    """Raised when a request value breaks an input rule. The message is safe to return to the client."""


class AuthorizationError(Exception):
    """Raised when a request refers to data the caller does not own. The message is safe to return to the client."""
