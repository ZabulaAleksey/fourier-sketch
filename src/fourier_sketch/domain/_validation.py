"""Shared validation helpers for domain value objects."""

from math import isfinite

from .errors import DomainValidationError


def finite_float(value: float, *, field_name: str) -> float:
    """Return a canonical float or raise a domain-specific validation error."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DomainValidationError(f"{field_name} must be a real number")

    try:
        normalized = float(value)
    except (OverflowError, ValueError) as error:
        raise DomainValidationError(f"{field_name} must be a finite real number") from error
    if not isfinite(normalized):
        raise DomainValidationError(f"{field_name} must be finite")
    return normalized


def finite_complex(value: complex, *, field_name: str) -> complex:
    """Return a canonical complex number whose components are finite."""
    if isinstance(value, bool) or not isinstance(value, (int, float, complex)):
        raise DomainValidationError(f"{field_name} must be a complex-compatible number")

    try:
        normalized = complex(value)
    except (OverflowError, ValueError) as error:
        raise DomainValidationError(
            f"{field_name} must have finite real and imaginary parts"
        ) from error
    if not isfinite(normalized.real) or not isfinite(normalized.imag):
        raise DomainValidationError(f"{field_name} must have finite real and imaginary parts")
    return normalized


def integer(value: int, *, field_name: str) -> int:
    """Validate a strict integer, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainValidationError(f"{field_name} must be an integer")
    return value


def immutable_tuple[T](value: tuple[T, ...], *, field_name: str) -> tuple[T, ...]:
    """Copy an iterable into immutable storage or raise a typed domain error."""
    try:
        return tuple(value)
    except TypeError as error:
        raise DomainValidationError(f"{field_name} must be an iterable collection") from error
