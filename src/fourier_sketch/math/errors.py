"""Errors raised by explicit numerical backends."""


class FourierBackendError(RuntimeError):
    """Raised when a selected numerical backend cannot complete its operation."""
