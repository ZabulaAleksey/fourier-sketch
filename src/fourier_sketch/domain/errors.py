"""Domain-specific errors."""


class DomainValidationError(ValueError):
    """Raised when a domain value cannot satisfy its structural invariants."""
