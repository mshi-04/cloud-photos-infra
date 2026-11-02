class ValidationError(ValueError):
    """Raised when a request value breaks an input rule. The message is safe to return to the client."""
