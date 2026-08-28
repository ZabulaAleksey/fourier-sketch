"""Conversions between planar domain values and built-in complex samples."""

from collections.abc import Sequence

from fourier_sketch.domain import Curve, DomainValidationError, Point2D

from ._validation import finite_complex_samples, finite_complex_value


def point_to_complex(point: Point2D) -> complex:
    """Encode a Cartesian point as ``x + i*y``."""
    if not isinstance(point, Point2D):
        raise DomainValidationError("point must be a Point2D")
    return complex(point.x, point.y)


def complex_to_point(value: complex) -> Point2D:
    """Decode a finite complex value into a Cartesian point."""
    normalized = finite_complex_value(value, field_name="value")
    return Point2D(normalized.real, normalized.imag)


def curve_to_complex_samples(curve: Curve) -> tuple[complex, ...]:
    """Convert an ordered curve without changing sample order or topology metadata."""
    if not isinstance(curve, Curve):
        raise DomainValidationError("curve must be a Curve")
    return tuple(point_to_complex(point) for point in curve.points)


def complex_samples_to_curve(
    samples: Sequence[complex],
    *,
    closed: bool,
) -> Curve:
    """Convert ordered samples into a curve with explicit open/closed semantics."""
    values = finite_complex_samples(samples)
    return Curve(tuple(complex_to_point(value) for value in values), closed=closed)
