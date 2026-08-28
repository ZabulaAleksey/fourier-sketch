"""Validation helpers shared by numerical modules."""

from collections.abc import Sequence
from math import isfinite

from fourier_sketch.domain import DomainValidationError


def finite_complex_value(value: complex, *, field_name: str) -> complex:
    """Return a built-in finite complex value."""
    if isinstance(value, bool) or not isinstance(value, (int, float, complex)):
        raise DomainValidationError(f"{field_name} must be a complex-compatible number")
    try:
        normalized = complex(value)
    except (OverflowError, ValueError) as error:
        raise DomainValidationError(f"{field_name} must be finite") from error
    if not isfinite(normalized.real) or not isfinite(normalized.imag):
        raise DomainValidationError(f"{field_name} must be finite")
    return normalized


def finite_complex_samples(
    samples: Sequence[complex],
    *,
    max_count: int | None = None,
) -> tuple[complex, ...]:
    """Validate and canonicalize a non-empty finite sample sequence."""
    try:
        sample_count = len(samples)
    except TypeError as error:
        raise DomainValidationError("samples must be an iterable collection") from error
    if sample_count == 0:
        raise DomainValidationError("samples must contain at least one value")
    if max_count is not None and sample_count > max_count:
        raise DomainValidationError(f"samples must contain at most {max_count} values")
    values = tuple(samples)
    return tuple(
        finite_complex_value(value, field_name=f"samples[{index}]")
        for index, value in enumerate(values)
    )
