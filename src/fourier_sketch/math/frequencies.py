"""Canonical signed-frequency mapping for FFT storage indices."""

from fourier_sketch.domain import DomainValidationError


def _positive_integer(value: int, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DomainValidationError(f"{field_name} must be a positive integer")
    return value


def signed_frequency(index: int, sample_count: int) -> int:
    """Map one FFT storage index to the canonical signed frequency label."""
    count = _positive_integer(sample_count, field_name="sample_count")
    if isinstance(index, bool) or not isinstance(index, int):
        raise DomainValidationError("index must be an integer")
    if index < 0 or index >= count:
        raise DomainValidationError("index must satisfy 0 <= index < sample_count")
    if index <= (count - 1) // 2:
        return index
    return index - count


def signed_frequencies(sample_count: int) -> tuple[int, ...]:
    """Return all canonical labels in FFT storage order."""
    count = _positive_integer(sample_count, field_name="sample_count")
    return tuple(signed_frequency(index, count) for index in range(count))
